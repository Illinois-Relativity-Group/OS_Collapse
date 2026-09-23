import bpy, mathutils

#initialize time node group
def time_node_group():
    time = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "time")

    time.color_tag = 'NONE'
    time.description = ""
    

    time.is_modifier = True

    #time interface
    #Socket Geometry
    geometry_socket = time.interface.new_socket(name = "Geometry", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    #Socket Geometry
    geometry_socket_1 = time.interface.new_socket(name = "Geometry", in_out='INPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'

    #Socket Size
    size_socket = time.interface.new_socket(name = "Size", in_out='INPUT', socket_type = 'NodeSocketFloat')
    size_socket.default_value = 33.599998474121094
    size_socket.min_value = 0.0
    size_socket.max_value = 3.4028234663852886e+38
    size_socket.subtype = 'DISTANCE'
    size_socket.attribute_domain = 'POINT'


    #initialize time nodes
    #node Group Input
    group_input = time.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    #node Group Output
    group_output = time.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    #node String to Curves
    string_to_curves = time.nodes.new("GeometryNodeStringToCurves")
    string_to_curves.name = "String to Curves"
    string_to_curves.align_x = 'CENTER'
    string_to_curves.align_y = 'TOP_BASELINE'
    string_to_curves.overflow = 'OVERFLOW'
    string_to_curves.pivot_mode = 'BOTTOM_LEFT'
    #Character Spacing
    string_to_curves.inputs[2].default_value = 1.0
    #Word Spacing
    string_to_curves.inputs[3].default_value = 1.0
    #Line Spacing
    string_to_curves.inputs[4].default_value = 1.0
    #Text Box Width
    string_to_curves.inputs[5].default_value = 0.0

    #node Value to String
    value_to_string = time.nodes.new("FunctionNodeValueToString")
    value_to_string.name = "Value to String"
    #Value
    value_to_string.inputs[0].default_value = 119.4000015258789
    #Decimals
    value_to_string.inputs[1].default_value = 0

    #node Fill Curve
    fill_curve = time.nodes.new("GeometryNodeFillCurve")
    fill_curve.name = "Fill Curve"
    # fill_curve.mode = 'TRIANGLES'   # Blender 5.0: GeometryNodeFillCurve.mode removed; default fill is fine
    #Group ID
    fill_curve.inputs[1].default_value = 0

    #node Set Material
    set_material = time.nodes.new("GeometryNodeSetMaterial")
    set_material.name = "Set Material"
    #Selection
    set_material.inputs[1].default_value = True
    if "letter.001" in bpy.data.materials:
        set_material.inputs[2].default_value = bpy.data.materials["letter.001"]

    #node Join Strings
    join_strings = time.nodes.new("GeometryNodeStringJoin")
    join_strings.name = "Join Strings"
    #Delimiter
    join_strings.inputs[0].default_value = ""

    #node String
    string = time.nodes.new("FunctionNodeInputString")
    string.name = "String"
    string.string = "t/M = "

    #node Realize Instances
    realize_instances = time.nodes.new("GeometryNodeRealizeInstances")
    realize_instances.name = "Realize Instances"
    #Selection
    realize_instances.inputs[1].default_value = True
    #Realize All
    realize_instances.inputs[2].default_value = True
    #Depth
    realize_instances.inputs[3].default_value = 0





    #Set locations
    group_input.location = (-519.5186767578125, -8.935356140136719)
    group_output.location = (1123.4998779296875, 0.0)
    string_to_curves.location = (235.25375366210938, 85.41909790039062)
    value_to_string.location = (-310.88604736328125, -113.82766723632812)
    fill_curve.location = (465.32000732421875, 69.72634887695312)
    set_material.location = (763.4998168945312, 48.837162017822266)
    join_strings.location = (55.24317932128906, -138.37362670898438)
    string.location = (-177.4375762939453, -230.27056884765625)
    realize_instances.location = (943.5000610351562, 73.47638702392578)

    #Set dimensions
    group_input.width, group_input.height = 140.0, 100.0
    group_output.width, group_output.height = 140.0, 100.0
    string_to_curves.width, string_to_curves.height = 190.0, 100.0
    value_to_string.width, value_to_string.height = 140.0, 100.0
    fill_curve.width, fill_curve.height = 140.0, 100.0
    set_material.width, set_material.height = 140.0, 100.0
    join_strings.width, join_strings.height = 140.0, 100.0
    string.width, string.height = 140.0, 100.0
    realize_instances.width, realize_instances.height = 140.0, 100.0

    #initialize time links
    #join_strings.String -> string_to_curves.String
    time.links.new(join_strings.outputs[0], string_to_curves.inputs[0])
    #realize_instances.Geometry -> group_output.Geometry
    time.links.new(realize_instances.outputs[0], group_output.inputs[0])
    #string_to_curves.Curve Instances -> fill_curve.Curve
    time.links.new(string_to_curves.outputs[0], fill_curve.inputs[0])
    #group_input.Size -> string_to_curves.Size
    time.links.new(group_input.outputs[1], string_to_curves.inputs[1])
    #value_to_string.String -> join_strings.Strings
    time.links.new(value_to_string.outputs[0], join_strings.inputs[1])
    #fill_curve.Mesh -> set_material.Geometry
    time.links.new(fill_curve.outputs[0], set_material.inputs[0])
    #set_material.Geometry -> realize_instances.Geometry
    time.links.new(set_material.outputs[0], realize_instances.inputs[0])
    #string.String -> join_strings.Strings
    time.links.new(string.outputs[0], join_strings.inputs[1])
    return time

# time = time_node_group()   # leftover module-level demo call; do not build node group on import

