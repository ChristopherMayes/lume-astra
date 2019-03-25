import subprocess
import os, errno

def execute(cmd):
    """
    
    Constantly print Subprocess output while process is running
    from: https://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
    
    # Example usage:
        for path in execute(["locate", "a"]):
        print(path, end="")
        
    Useful in Jupyter notebook
    
    """
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line 
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)
        
        
        
def runs_script(runscript=[], dir=None, log_file=None, verbose=True):
    """
    Basic driver for running a script in a directory. Will     
    """

    # Save init dir
    init_dir = os.getcwd()
    
    if dir:
        os.chdir(dir)
 
    log = []
    
    for path in execute(runscript):
         if verbose:
            print(path, end="")
         log.append(path)
    if log_file:
        with open(log_file, 'w') as f:
            for line in log:
                f.write(line)    
    
    # Return to init dir
    os.chdir(init_dir)                
    return log                    


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
    
    
def replace_parameters(templatefile, outfile, replacements, delims='=', commentchar=None, endchars = '\n', warn=False): 
  """ looks for strings of the form:
  PARAM delim VALUE, if delim is a single str
  and if PARAM is in replacements, writes a new line:
  PARAM delim replacements[PARAM], otherwise does the replacement:
  PARAM delim[0] VALUE delim[1] -> PARAM delim[0] replacement[PARAM] delim[1]
  if warn, a warning will be printed if a parameter is not in the file
  if commentchar, enchars will be replaced by the comment (if the line has a comment)

  Returns boolean signifying if parameter was replaced successfully
  """
  t = open(templatefile, 'r')
  f = open(outfile, 'w')

  param_set = True

  # count the number of replacements
  count = {}
  for key in replacements:
    count[key] = 0
  for line in t:
 
    if(isinstance(delims,str)):  # DEFAULT: ONLY ONE DELIMITER
      #print("One delim only")
      delim = delims
      s = line.split(delim)
      if len(s) == 1:
        f.write(line)
      else:
        for key in replacements:
          if s[0].strip() == key:
            if commentchar:
              comment=line.split(commentchar, 1)
              if len(comment) > 1:
                endchars = ' '+commentchar+comment[1]
            count[key] += 1
            line = key + delim + str(replacements[key]) + endchars
        f.write(line)
        param_set=True

    else: # ADD OPTION FOR TWO DELIMITERS
      s = line.split(delims[0])
      if len(s) == 1:
        #print(line)
        f.write(line)   # prints blank lines
      else:
        for key in replacements:
          if s[0].strip() == key:
            #print(line)
            if commentchar:
              line_split_on_comment=line.split(commentchar, 1)
              assignment_str = line_split_on_comment[0]
              if(len(line_split_on_comment)>1):
                endchars_new = " " + commentchar + line_split_on_comment[1] 
              else:
                endchars_new = endchars
            else:
              assignment_str = line
              endchars_new = endchars
            #print(assignment_str,endchars_new)
            rtokens = assignment_str.split(delims[1])
            #print(rtokens)

            tokens=[]
            for token in rtokens:
              if(token!=""):
                tokens.append(token)

            if(delims[0]==delims[1]):
              remainder_str = delims[1].join(tokens[2:])
            else:
              remainder_str = delims[1].join(tokens[1:])
            #print(remainder_str+".")
            if(len(remainder_str.split("\n")) > 1 and endchars=="\n"):
               remainder_str = remainder_str.split("\n")[0]

            line = key + delims[0] + str(replacements[key]) + delims[1] + remainder_str + endchars_new
           
            #print(line)
            count[key] += 1

        f.write(line)
      
  t.close()
  f.close()
  
  if warn:
    for key in count:
      c = count[key]
      if c == 0:
        print('Warning: '+templatefile+' : No replacements for '+key)
        param_set=False
      if c > 1:
        print('Warning: '+templatefile+' : Multiple ('+str(c)+') replacements for '+key) 
        param_set = False
  return param_set    