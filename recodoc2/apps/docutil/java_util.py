from __future__ import unicode_literals

def clean_java_name(name):
    """Given a name, returns a tuple containing the simple name and the fully
    qualified name. Removes all array or generic artifacts.
    """
    # Replaces inner class artifact
    clean_name_fqn = name.replace('$','.')

    # Clean Array
    index = clean_name_fqn.find('[')
    if index > -1:
        clean_name_fqn = clean_name_fqn[:index]

    # Clean Generic
    index = clean_name_fqn.find('<')
    if index > -1:
        clean_name_fqn = clean_name_fqn[:index]
    
    dot_index = clean_name_fqn.rfind('.')
    clean_name_simple = clean_name_fqn
    if dot_index > -1:
        clean_name_simple = clean_name_fqn[dot_index+1:]
        
    return (clean_name_simple, clean_name_fqn)
