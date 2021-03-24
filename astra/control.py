import json

class ControlGroup:
    """
    Group elements to control the attributes for a list of elements. 
    
    Based on Bmad's Ovelay and Group elements
    
    If absolute, the underlying attributes will be set absolutely. 
    
    Othereise, underlying attributes will be set to changes from reference_values.
    
    If reference values are not given, they will be set when linking elements. 
    
    Otherwise, only changes will be set. 
    
    Optionally, a list of factors can be used 
    
    Example 1:
        ELES = {'a':{'x':1}, 'b':{'x':2}}
        G = ControlGroup(ele_names=['a', 'b'], var_name='x')
        G.link(ELES) # This will set .reference_values = [1, 2]
        G['x'] = 3 
        G.eles
    Returns:
        {'a': {'x': 4.0}, 'b': {'x': 5.0}}
    
    Example 2:
        ELES = {'a':{'x':1}, 'b':{'x':2}}
        G = ControlGroup(ele_names=['a', 'b'], var_name='dx', attributes='x', factors = [1.0, 2.0], absolute=False)
        G.link(ELES)
        G['dx'] = 3
        G.eles
    Returns:  
        {'a': {'x': 4.0}, 'b': {'x': 8.0}})

    """
    def __init__(self, 
                 ele_names=[], 
                 var_name=None,
                 # If underlying attribute is different
                 attributes=None, 
                 # If factors != 1 
                 factors = None,
                 reference_values = None,
                 value=0,
                 absolute=False # 
                ):
        
        # Allow single element
        if isinstance(ele_names, str):
            ele_names = [ele_names]
            
        self.ele_names = ele_names # Link these. 
        self.var_name = var_name
        
        self.attributes = attributes
        self.factors = factors
        self.reference_values = None
        
        self.absolute = absolute
        
        n_ele = len(self.ele_names)
        
        if not self.attributes:
            self.attributes = n_ele * [self.var_name]
        elif isinstance(self.attributes, str):
            self.attributes = n_ele * [self.attributes]
            
        assert len(self.attributes) == n_ele, 'attributes should be a list with the same length as ele_names'
        
        if not self.factors:
            self.factors = n_ele * [1.0]
        else:
            self.factors = [float(f) for f in self.factors] # Cast to float for YAML safety    
        assert len(self.factors) == n_ele, 'factors should be a list with the same length as ele_names'
        
        if reference_values:
            self.reference_values = [float(f) for f in self.reference_values]
        
        self.value = float(value) # Cast to float for YAML safety
        
        # These need to be linked by the .link function
        self.ele_dict=None

    def link(self, ele_dict):
        """
        Link and ele dict, so that update will work
        """
        self.ele_dict=ele_dict
        # Populate reference values if none were defined
        if not self.reference_values:
            self.reference_values = self.ele_values
        
        # call setter
        self[self.var_name] = self.value
        
    @property
    def eles(self):
        """Return a list of the controlled eles"""
        return [self.ele_dict[name] for name in self.ele_names]  
    
    @property
    def ele_values(self):
        """Returns the underlying element values"""        
        return [self.ele_dict[ele_name][attrib] for ele_name, attrib in zip(self.ele_names, self.attributes)]

    
    def set_absolute(self, key, item):
        """
        Sets the underlying attributes directly. 
        """
        self.value = item
        
        for name, attrib, f in zip(self.ele_names, self.attributes, self.factors):
            self.ele_dict[name][attrib] = f * self.value        
        
    def set_delta(self, key, item):
        """
        Sets a change (delta) in the underlying attributes. 
        """
        
        self.value = item     
        for name, attrib, f, ref in zip(self.ele_names, self.attributes, self.factors, self.reference_values):
            self.ele_dict[name][attrib] = ref + f * self.value
        
    def __setitem__(self, key, item):
        """
        Calls the appropriate set routine: set_absolute or set_delta
        """
        assert key == self.var_name, f'{key} mismatch var_name: {self.var_name}'
        
        assert self.eles, 'No eles are linked. Please call .link(eles)'
        
        if self.absolute:
            self.set_absolute(key, item)
        else:
            self.set_delta(key, item)    
        
    def __getitem__(self, key):
        assert key == self.var_name
        return self.value
    
    def __str__(self):
        
        if self.absolute:
            s2 = 'absolute'
        else:
            s2 = 'changes in'
            
        s = f'{self.__class__.__name__} of eles {self.ele_names} with variable {self.var_name} controlling {s2} {self.attributes} with factors {self.factors}'            
        return s
    
    def dumps(self):
        """
        Dump the internal data as a JSON string
        """
        ele_dict = self.__dict__.pop('ele_dict')
        d = self.__dict__
        s = json.dumps(d)
        # Relink
        self.ele_dict = ele_dict
        return s
    
    def loads(self, s):
        """
        Loads from a JSON string. See .dumps()
        """
        d = json.loads(s)
        self.__dict__.update(d)
    
    def __repr__(self):
        
        s0 = self.dumps()
        s = f'{self.__class__.__name__}(**{s0})'
        
        return s 


    