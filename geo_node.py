import bpy
import mathutils
import os
import typing


def node_group_for_ply(node_tree_names: dict[typing.Callable, str]):
    """Initialize NodeGroup node group"""
    nodegroup_1 = bpy.data.node_groups.new(type='GeometryNodeTree', name="NodeGroup")

    nodegroup_1.color_tag = 'NONE'
    nodegroup_1.description = ""
    nodegroup_1.default_group_node_width = 140
    nodegroup_1.show_modifier_manage_panel = True

    # nodegroup_1 interface

    # Socket Mesh
    mesh_socket = nodegroup_1.interface.new_socket(name="Mesh", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    mesh_socket.attribute_domain = 'POINT'
    mesh_socket.default_input = 'VALUE'
    mesh_socket.structure_type = 'AUTO'

    # Socket Path
    path_socket = nodegroup_1.interface.new_socket(name="Path", in_out='INPUT', socket_type='NodeSocketString')
    path_socket.default_value = "/data/yliang3/magnetised_star/magnetised_star_collapse_3d/equipotential_lines.ply"
    path_socket.subtype = 'FILE_PATH'
    path_socket.attribute_domain = 'POINT'
    path_socket.description = "Path to a PLY file"
    path_socket.default_input = 'VALUE'
    path_socket.structure_type = 'AUTO'
    path_socket.optional_label = True

    # Socket Radius
    radius_socket = nodegroup_1.interface.new_socket(name="Radius", in_out='INPUT', socket_type='NodeSocketFloat')
    radius_socket.default_value = 0.019999999552965164
    radius_socket.min_value = 0.0
    radius_socket.max_value = 3.4028234663852886e+38
    radius_socket.subtype = 'DISTANCE'
    radius_socket.attribute_domain = 'POINT'
    radius_socket.description = "Distance of the points from the origin"
    radius_socket.default_input = 'VALUE'
    radius_socket.structure_type = 'AUTO'

    # Initialize nodegroup_1 nodes

    # Node Group Output
    group_output = nodegroup_1.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Group Input
    group_input = nodegroup_1.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Import PLY
    import_ply = nodegroup_1.nodes.new("GeometryNodeImportPLY")
    import_ply.name = "Import PLY"

    # Node Mesh to Points
    mesh_to_points = nodegroup_1.nodes.new("GeometryNodeMeshToPoints")
    mesh_to_points.name = "Mesh to Points"
    mesh_to_points.mode = 'VERTICES'
    # Selection
    mesh_to_points.inputs[1].default_value = True
    # Position
    mesh_to_points.inputs[2].default_value = (0.0, 0.0, 0.0)
    # Radius
    mesh_to_points.inputs[3].default_value = 0.05000000074505806

    # Node Points to Curves
    points_to_curves = nodegroup_1.nodes.new("GeometryNodePointsToCurves")
    points_to_curves.name = "Points to Curves"
    # Curve Group ID
    points_to_curves.inputs[1].default_value = 0
    # Weight
    points_to_curves.inputs[2].default_value = 0.0

    # Node Delete Geometry
    delete_geometry = nodegroup_1.nodes.new("GeometryNodeDeleteGeometry")
    delete_geometry.name = "Delete Geometry"
    delete_geometry.domain = 'EDGE'
    delete_geometry.mode = 'ALL'

    # Node Curve to Mesh
    curve_to_mesh = nodegroup_1.nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.name = "Curve to Mesh"
    # Scale
    curve_to_mesh.inputs[2].default_value = 1.0
    # Fill Caps
    curve_to_mesh.inputs[3].default_value = False

    # Node Edge Length
    edge_length = nodegroup_1.nodes.new("GeometryNodeGroup")
    edge_length.name = "Edge Length"
    # Finding linked library node group
    for node_group in bpy.data.node_groups:
        if (
            node_group.name == "Edge Length"
            and node_group.bl_idname == 'GeometryNodeTree'
        ):
            edge_length.node_tree = node_group
    if edge_length.node_tree is None:
        print("Couldn't find node group Edge Length, failing")
        return

    # Node Math
    math = nodegroup_1.nodes.new("ShaderNodeMath")
    math.name = "Math"
    math.operation = 'GREATER_THAN'
    math.use_clamp = False
    # Value_001
    math.inputs[1].default_value = 0.5


    # Node Curve Circle
    curve_circle = nodegroup_1.nodes.new("GeometryNodeCurvePrimitiveCircle")
    curve_circle.name = "Curve Circle"
    curve_circle.mode = 'RADIUS'
    # Resolution
    curve_circle.inputs[0].default_value = 5

    # Node Mesh to Curve
    mesh_to_curve = nodegroup_1.nodes.new("GeometryNodeMeshToCurve")
    mesh_to_curve.name = "Mesh to Curve"
    mesh_to_curve.mode = 'EDGES'
    # Selection
    mesh_to_curve.inputs[1].default_value = True

    # Node Curve to Mesh.001
    curve_to_mesh_001 = nodegroup_1.nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh_001.name = "Curve to Mesh.001"
    # Scale
    curve_to_mesh_001.inputs[2].default_value = 1.0
    # Fill Caps
    curve_to_mesh_001.inputs[3].default_value = False

    # Node Viewer
    viewer = nodegroup_1.nodes.new("GeometryNodeViewer")
    viewer.name = "Viewer"
    viewer.active_index = 0
    viewer.domain = 'AUTO'
    viewer.ui_shortcut = 0
    viewer.viewer_items.clear()
    viewer.viewer_items.new('GEOMETRY', "Mesh")

    # Set locations
    nodegroup_1.nodes["Group Output"].location = (1189.4630126953125, 179.99461364746094)
    nodegroup_1.nodes["Group Input"].location = (-816.1386108398438, 18.00994873046875)
    nodegroup_1.nodes["Import PLY"].location = (-610.3592529296875, 159.36595153808594)
    nodegroup_1.nodes["Mesh to Points"].location = (-400.56744384765625, 197.33981323242188)
    nodegroup_1.nodes["Points to Curves"].location = (-220.80101013183594, 213.01707458496094)
    nodegroup_1.nodes["Delete Geometry"].location = (576.733154296875, 290.8379821777344)
    nodegroup_1.nodes["Curve to Mesh"].location = (163.22654724121094, 290.1935729980469)
    nodegroup_1.nodes["Edge Length"].location = (126.67112731933594, 11.059951782226562)
    nodegroup_1.nodes["Math"].location = (313.6068115234375, 160.72933959960938)
    nodegroup_1.nodes["Curve Circle"].location = (636.509033203125, 79.79248046875)
    nodegroup_1.nodes["Mesh to Curve"].location = (781.797119140625, 329.2680358886719)
    nodegroup_1.nodes["Curve to Mesh.001"].location = (999.4630126953125, 348.9292907714844)
    nodegroup_1.nodes["Viewer"].location = (-450.5, 314.5)

    # Set dimensions
    nodegroup_1.nodes["Group Output"].width  = 140.0
    nodegroup_1.nodes["Group Output"].height = 100.0

    nodegroup_1.nodes["Group Input"].width  = 140.0
    nodegroup_1.nodes["Group Input"].height = 100.0

    nodegroup_1.nodes["Import PLY"].width  = 140.0
    nodegroup_1.nodes["Import PLY"].height = 100.0

    nodegroup_1.nodes["Mesh to Points"].width  = 140.0
    nodegroup_1.nodes["Mesh to Points"].height = 100.0

    nodegroup_1.nodes["Points to Curves"].width  = 140.0
    nodegroup_1.nodes["Points to Curves"].height = 100.0

    nodegroup_1.nodes["Delete Geometry"].width  = 140.0
    nodegroup_1.nodes["Delete Geometry"].height = 100.0

    nodegroup_1.nodes["Curve to Mesh"].width  = 140.0
    nodegroup_1.nodes["Curve to Mesh"].height = 100.0

    nodegroup_1.nodes["Edge Length"].width  = 140.0
    nodegroup_1.nodes["Edge Length"].height = 100.0

    nodegroup_1.nodes["Math"].width  = 140.0
    nodegroup_1.nodes["Math"].height = 100.0

    nodegroup_1.nodes["Curve Circle"].width  = 140.0
    nodegroup_1.nodes["Curve Circle"].height = 100.0

    nodegroup_1.nodes["Mesh to Curve"].width  = 140.0
    nodegroup_1.nodes["Mesh to Curve"].height = 100.0

    nodegroup_1.nodes["Curve to Mesh.001"].width  = 140.0
    nodegroup_1.nodes["Curve to Mesh.001"].height = 100.0

    nodegroup_1.nodes["Viewer"].width  = 140.0
    nodegroup_1.nodes["Viewer"].height = 100.0


    # Initialize nodegroup_1 links

    # points_to_curves.Curves -> curve_to_mesh.Curve
    nodegroup_1.links.new(
        nodegroup_1.nodes["Points to Curves"].outputs[0],
        nodegroup_1.nodes["Curve to Mesh"].inputs[0]
    )
    # curve_to_mesh.Mesh -> delete_geometry.Geometry
    nodegroup_1.links.new(
        nodegroup_1.nodes["Curve to Mesh"].outputs[0],
        nodegroup_1.nodes["Delete Geometry"].inputs[0]
    )
    # mesh_to_points.Points -> points_to_curves.Points
    nodegroup_1.links.new(
        nodegroup_1.nodes["Mesh to Points"].outputs[0],
        nodegroup_1.nodes["Points to Curves"].inputs[0]
    )
    # import_ply.Mesh -> mesh_to_points.Mesh
    nodegroup_1.links.new(
        nodegroup_1.nodes["Import PLY"].outputs[0],
        nodegroup_1.nodes["Mesh to Points"].inputs[0]
    )
    # curve_circle.Curve -> curve_to_mesh_001.Profile Curve
    nodegroup_1.links.new(
        nodegroup_1.nodes["Curve Circle"].outputs[0],
        nodegroup_1.nodes["Curve to Mesh.001"].inputs[1]
    )
    # delete_geometry.Geometry -> mesh_to_curve.Mesh
    nodegroup_1.links.new(
        nodegroup_1.nodes["Delete Geometry"].outputs[0],
        nodegroup_1.nodes["Mesh to Curve"].inputs[0]
    )
    # math.Value -> delete_geometry.Selection
    nodegroup_1.links.new(
        nodegroup_1.nodes["Math"].outputs[0],
        nodegroup_1.nodes["Delete Geometry"].inputs[1]
    )
    # mesh_to_curve.Curve -> curve_to_mesh_001.Curve
    nodegroup_1.links.new(
        nodegroup_1.nodes["Mesh to Curve"].outputs[0],
        nodegroup_1.nodes["Curve to Mesh.001"].inputs[0]
    )
    # edge_length.Length -> math.Value
    nodegroup_1.links.new(
        nodegroup_1.nodes["Edge Length"].outputs[0],
        nodegroup_1.nodes["Math"].inputs[0]
    )
    # curve_to_mesh_001.Mesh -> group_output.Mesh
    nodegroup_1.links.new(
        nodegroup_1.nodes["Curve to Mesh.001"].outputs[0],
        nodegroup_1.nodes["Group Output"].inputs[0]
    )
    # group_input.Path -> import_ply.Path
    nodegroup_1.links.new(
        nodegroup_1.nodes["Group Input"].outputs[0],
        nodegroup_1.nodes["Import PLY"].inputs[0]
    )
    # group_input.Radius -> curve_circle.Radius
    nodegroup_1.links.new(
        nodegroup_1.nodes["Group Input"].outputs[1],
        nodegroup_1.nodes["Curve Circle"].inputs[4]
    )
    # import_ply.Mesh -> viewer.Mesh
    nodegroup_1.links.new(
        nodegroup_1.nodes["Import PLY"].outputs[0],
        nodegroup_1.nodes["Viewer"].inputs[0]
    )
    viewer.viewer_items[0].auto_remove = True

    return nodegroup_1


# Import node groups from Blender essentials library
datafiles_path = bpy.utils.system_resource('DATAFILES')
lib_relpath = "assets/nodes/geometry_nodes_essentials.blend"
lib_path = os.path.join(datafiles_path, lib_relpath)
with bpy.data.libraries.load(lib_path, link=True)  as (data_src, data_dst):
	data_dst.node_groups = []
	if "Edge Length" in data_src.node_groups:
		data_dst.node_groups.append("Edge Length")


def field_line_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize field_line node group"""
    field_line_1 = bpy.data.node_groups.new(type='GeometryNodeTree', name="field_line")

    field_line_1.color_tag = 'NONE'
    field_line_1.description = ""
    field_line_1.default_group_node_width = 140
    field_line_1.is_modifier = True
    field_line_1.show_modifier_manage_panel = True

    # field_line_1 interface

    # Socket Geometry
    geometry_socket = field_line_1.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'
    geometry_socket.default_input = 'VALUE'
    geometry_socket.structure_type = 'AUTO'

    # Socket Geometry
    geometry_socket_1 = field_line_1.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'
    geometry_socket_1.default_input = 'VALUE'
    geometry_socket_1.structure_type = 'AUTO'

    # Socket Path
    path_socket = field_line_1.interface.new_socket(name="Path", in_out='INPUT', socket_type='NodeSocketString')
    path_socket.default_value = "/data/yliang3/magnetised_star/magnetised_star_collapse_3d/equipotential_lines.ply"
    path_socket.subtype = 'FILE_PATH'
    path_socket.attribute_domain = 'POINT'
    path_socket.description = "Path to a PLY file"
    path_socket.default_input = 'VALUE'
    path_socket.structure_type = 'AUTO'
    path_socket.optional_label = True

    # Socket Radius
    radius_socket = field_line_1.interface.new_socket(name="Radius", in_out='INPUT', socket_type='NodeSocketFloat')
    radius_socket.default_value = 0.019999999552965164
    radius_socket.min_value = 0.0
    radius_socket.max_value = 3.4028234663852886e+38
    radius_socket.subtype = 'DISTANCE'
    radius_socket.attribute_domain = 'POINT'
    radius_socket.description = "Distance of the points from the origin"
    radius_socket.default_input = 'VALUE'
    radius_socket.structure_type = 'AUTO'

    # Socket Value
    value_socket = field_line_1.interface.new_socket(name="Value", in_out='INPUT', socket_type='NodeSocketInt')
    value_socket.default_value = 0
    value_socket.min_value = -2147483648
    value_socket.max_value = 2147483647
    value_socket.subtype = 'NONE'
    value_socket.attribute_domain = 'POINT'
    value_socket.default_input = 'VALUE'
    value_socket.structure_type = 'AUTO'

    # Initialize field_line_1 nodes

    # Node Group Input
    group_input = field_line_1.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Group Output
    group_output = field_line_1.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Viewer
    viewer = field_line_1.nodes.new("GeometryNodeViewer")
    viewer.name = "Viewer"
    viewer.active_index = 0
    viewer.domain = 'AUTO'
    viewer.ui_shortcut = 0
    viewer.viewer_items.clear()
    viewer.viewer_items.new('GEOMETRY', "Geometry")

    # Node Group
    group = field_line_1.nodes.new("GeometryNodeGroup")
    group.name = "Group"
    group.node_tree = bpy.data.node_groups[node_tree_names[node_group_for_ply]]

    # Node Join Geometry
    join_geometry = field_line_1.nodes.new("GeometryNodeJoinGeometry")
    join_geometry.name = "Join Geometry"

    # Node Ico Sphere
    ico_sphere = field_line_1.nodes.new("GeometryNodeMeshIcoSphere")
    ico_sphere.name = "Ico Sphere"
    # Radius
    ico_sphere.inputs[0].default_value = 0 #TEMP_YINUANs
    # Subdivisions
    ico_sphere.inputs[1].default_value = 5

    # Node Geometry to Instance
    geometry_to_instance = field_line_1.nodes.new("GeometryNodeGeometryToInstance")
    geometry_to_instance.name = "Geometry to Instance"

    # Node Join Geometry.001
    join_geometry_001 = field_line_1.nodes.new("GeometryNodeJoinGeometry")
    join_geometry_001.name = "Join Geometry.001"

    # Node Repeat Input
    repeat_input = field_line_1.nodes.new("GeometryNodeRepeatInput")
    repeat_input.name = "Repeat Input"
    # Node Repeat Output
    repeat_output = field_line_1.nodes.new("GeometryNodeRepeatOutput")
    repeat_output.name = "Repeat Output"
    repeat_output.active_index = 0
    repeat_output.inspection_index = 0
    repeat_output.repeat_items.clear()
    # Create item "Geometry"
    repeat_output.repeat_items.new('GEOMETRY', "Geometry")

    # Node Transform Geometry
    transform_geometry = field_line_1.nodes.new("GeometryNodeTransform")
    transform_geometry.name = "Transform Geometry"
    # Mode
    transform_geometry.inputs[1].default_value = 'Components'
    # Translation
    transform_geometry.inputs[2].default_value = (0.0, 0.0, 0.0)
    # Scale
    transform_geometry.inputs[4].default_value = (1.0, 1.0, 1.0)

    # Node Combine XYZ
    combine_xyz = field_line_1.nodes.new("ShaderNodeCombineXYZ")
    combine_xyz.name = "Combine XYZ"
    # X
    combine_xyz.inputs[0].default_value = 0.0
    # Z
    combine_xyz.inputs[2].default_value = 0.0

    # Node Math
    math = field_line_1.nodes.new("ShaderNodeMath")
    math.name = "Math"
    math.operation = 'DIVIDE'
    math.use_clamp = False
    # Value
    math.inputs[0].default_value = 3.1415927410125732

    # Node Set Material
    set_material = field_line_1.nodes.new("GeometryNodeSetMaterial")
    set_material.name = "Set Material"
    # Selection
    set_material.inputs[1].default_value = True
    if "test_volume" in bpy.data.materials:
        set_material.inputs[2].default_value = bpy.data.materials["test_volume"]

    # Node Set Material.001
    set_material_001 = field_line_1.nodes.new("GeometryNodeSetMaterial")
    set_material_001.name = "Set Material.001"
    # Selection
    set_material_001.inputs[1].default_value = True
    if "lines" in bpy.data.materials:
        set_material_001.inputs[2].default_value = bpy.data.materials["lines"]

    # Node Math.001
    math_001 = field_line_1.nodes.new("ShaderNodeMath")
    math_001.name = "Math.001"
    math_001.operation = 'SUBTRACT'
    math_001.use_clamp = False
    # Value_001
    math_001.inputs[1].default_value = 1.0

    # Process zone input Repeat Input
    repeat_input.pair_with_output(repeat_output)



    # Set locations
    field_line_1.nodes["Group Input"].location = (385.8336181640625, 71.64329528808594)
    field_line_1.nodes["Group Output"].location = (2626.6103515625, 115.64027404785156)
    field_line_1.nodes["Viewer"].location = (2421.101318359375, 369.1839599609375)
    field_line_1.nodes["Group"].location = (637.2692260742188, 161.26370239257812)
    field_line_1.nodes["Join Geometry"].location = (2143.270263671875, 313.4939880371094)
    field_line_1.nodes["Ico Sphere"].location = (778.829833984375, 381.8699951171875)
    field_line_1.nodes["Geometry to Instance"].location = (1099.02001953125, 159.09527587890625)
    field_line_1.nodes["Join Geometry.001"].location = (1818.572265625, 75.5021743774414)
    field_line_1.nodes["Repeat Input"].location = (1332.6787109375, 109.58036804199219)
    field_line_1.nodes["Repeat Output"].location = (2044.0584716796875, 204.0010986328125)
    field_line_1.nodes["Transform Geometry"].location = (1604.36865234375, -41.835933685302734)
    field_line_1.nodes["Combine XYZ"].location = (1319.5574951171875, -163.50306701660156)
    field_line_1.nodes["Math"].location = (1079.166748046875, -164.91171264648438)
    field_line_1.nodes["Set Material"].location = (1473.7965087890625, 310.41448974609375)
    field_line_1.nodes["Set Material.001"].location = (905.4411010742188, 140.77146911621094)
    field_line_1.nodes["Math.001"].location = (1007.816650390625, 14.900703430175781)

    # Set dimensions
    field_line_1.nodes["Group Input"].width  = 140.0
    field_line_1.nodes["Group Input"].height = 100.0

    field_line_1.nodes["Group Output"].width  = 140.0
    field_line_1.nodes["Group Output"].height = 100.0

    field_line_1.nodes["Viewer"].width  = 140.0
    field_line_1.nodes["Viewer"].height = 100.0

    field_line_1.nodes["Group"].width  = 140.0
    field_line_1.nodes["Group"].height = 100.0

    field_line_1.nodes["Join Geometry"].width  = 140.0
    field_line_1.nodes["Join Geometry"].height = 100.0

    field_line_1.nodes["Ico Sphere"].width  = 140.0
    field_line_1.nodes["Ico Sphere"].height = 100.0

    field_line_1.nodes["Geometry to Instance"].width  = 160.0
    field_line_1.nodes["Geometry to Instance"].height = 100.0

    field_line_1.nodes["Join Geometry.001"].width  = 140.0
    field_line_1.nodes["Join Geometry.001"].height = 100.0

    field_line_1.nodes["Repeat Input"].width  = 140.0
    field_line_1.nodes["Repeat Input"].height = 100.0

    field_line_1.nodes["Repeat Output"].width  = 140.0
    field_line_1.nodes["Repeat Output"].height = 100.0

    field_line_1.nodes["Transform Geometry"].width  = 140.0
    field_line_1.nodes["Transform Geometry"].height = 100.0

    field_line_1.nodes["Combine XYZ"].width  = 140.0
    field_line_1.nodes["Combine XYZ"].height = 100.0

    field_line_1.nodes["Math"].width  = 140.0
    field_line_1.nodes["Math"].height = 100.0

    field_line_1.nodes["Set Material"].width  = 140.0
    field_line_1.nodes["Set Material"].height = 100.0

    field_line_1.nodes["Set Material.001"].width  = 140.0
    field_line_1.nodes["Set Material.001"].height = 100.0

    field_line_1.nodes["Math.001"].width  = 140.0
    field_line_1.nodes["Math.001"].height = 100.0


    # Initialize field_line_1 links

    # group_input.Path -> group.Path
    field_line_1.links.new(
        field_line_1.nodes["Group Input"].outputs[1],
        field_line_1.nodes["Group"].inputs[0]
    )
    # join_geometry.Geometry -> group_output.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Join Geometry"].outputs[0],
        field_line_1.nodes["Group Output"].inputs[0]
    )
    # group_input.Radius -> group.Radius
    field_line_1.links.new(
        field_line_1.nodes["Group Input"].outputs[2],
        field_line_1.nodes["Group"].inputs[1]
    )
    # set_material_001.Geometry -> geometry_to_instance.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Set Material.001"].outputs[0],
        field_line_1.nodes["Geometry to Instance"].inputs[0]
    )
    # geometry_to_instance.Instances -> repeat_input.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Geometry to Instance"].outputs[0],
        field_line_1.nodes["Repeat Input"].inputs[1]
    )
    # join_geometry_001.Geometry -> repeat_output.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Join Geometry.001"].outputs[0],
        field_line_1.nodes["Repeat Output"].inputs[0]
    )
    # repeat_input.Geometry -> join_geometry_001.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Repeat Input"].outputs[1],
        field_line_1.nodes["Join Geometry.001"].inputs[0]
    )
    # repeat_input.Geometry -> transform_geometry.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Repeat Input"].outputs[1],
        field_line_1.nodes["Transform Geometry"].inputs[0]
    )
    # repeat_output.Geometry -> join_geometry.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Repeat Output"].outputs[0],
        field_line_1.nodes["Join Geometry"].inputs[0]
    )
    # join_geometry.Geometry -> viewer.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Join Geometry"].outputs[0],
        field_line_1.nodes["Viewer"].inputs[0]
    )
    # combine_xyz.Vector -> transform_geometry.Rotation
    field_line_1.links.new(
        field_line_1.nodes["Combine XYZ"].outputs[0],
        field_line_1.nodes["Transform Geometry"].inputs[3]
    )
    # group_input.Value -> math.Value
    field_line_1.links.new(
        field_line_1.nodes["Group Input"].outputs[3],
        field_line_1.nodes["Math"].inputs[1]
    )
    # math.Value -> combine_xyz.X
    field_line_1.links.new(
        field_line_1.nodes["Math"].outputs[0],
        field_line_1.nodes["Combine XYZ"].inputs[1]
    )
    # math_001.Value -> repeat_input.Iterations
    field_line_1.links.new(
        field_line_1.nodes["Math.001"].outputs[0],
        field_line_1.nodes["Repeat Input"].inputs[0]
    )
    # group.Mesh -> set_material_001.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Group"].outputs[0],
        field_line_1.nodes["Set Material.001"].inputs[0]
    )
    # group_input.Value -> math_001.Value
    field_line_1.links.new(
        field_line_1.nodes["Group Input"].outputs[3],
        field_line_1.nodes["Math.001"].inputs[0]
    )
    # ico_sphere.Mesh -> set_material.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Ico Sphere"].outputs[0],
        field_line_1.nodes["Set Material"].inputs[0]
    )
    # set_material.Geometry -> join_geometry.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Set Material"].outputs[0],
        field_line_1.nodes["Join Geometry"].inputs[0]
    )
    # transform_geometry.Geometry -> join_geometry_001.Geometry
    field_line_1.links.new(
        field_line_1.nodes["Transform Geometry"].outputs[0],
        field_line_1.nodes["Join Geometry.001"].inputs[0]
    )
    viewer.viewer_items[0].auto_remove = True

    return field_line_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    nodegroup = node_group_for_ply(node_tree_names)
    node_tree_names[node_group_for_ply] = nodegroup.name

    field_line = field_line_1_node_group(node_tree_names)
    node_tree_names[field_line_1_node_group] = field_line.name

