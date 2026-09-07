import bpy
import math
import os


# --------------------------------------------------
# Material
# --------------------------------------------------

def create_density_material(image_path):

    mat_name = "DensityMaterial"

    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(
            bpy.data.materials[mat_name],
            do_unlink=True
        )

    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    tex = nodes.new("ShaderNodeTexImage")
    tex.location = (-600, 0)

    tex.image = bpy.data.images.load(
        os.path.abspath(image_path)
    )

    mult = nodes.new("ShaderNodeMath")
    mult.operation = 'MULTIPLY'
    mult.inputs[1].default_value = 0.08
    mult.location = (-300, -150)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)

    bsdf.inputs["Metallic"].default_value = 0.7
    bsdf.inputs["Roughness"].default_value = 0.7 #0.3
    bsdf.inputs["Emission Strength"].default_value = 0.5
    #print(f"bsdf inputs: {bsdf.inputs.keys()}")

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)

    links.new(
        tex.outputs["Color"],
        bsdf.inputs["Base Color"]
    )

    links.new(
        tex.outputs["Color"],
        bsdf.inputs["Emission Color"]
    )

    links.new(
        tex.outputs["Alpha"],
        mult.inputs[0]
    )

    links.new(
        mult.outputs["Value"],
        bsdf.inputs["Alpha"]
    )

    links.new(
        bsdf.outputs["BSDF"],
        output.inputs["Surface"]
    )

    mat.blend_method = 'BLEND'

    return mat


# --------------------------------------------------
# Create one cylinder
# --------------------------------------------------

def create_axisymmetric_sweep(
        material,
        count=180,
        plane_size=6.0,
        axis='Y',
        name="DensityCylinder"):

    collection = bpy.context.collection

    #
    # Base plane
    #
    bpy.ops.mesh.primitive_plane_add(size=plane_size)

    base = bpy.context.active_object
    base.name = f"{name}_template"

    base.data.materials.clear()
    base.data.materials.append(material)

    #
    # Move plane so LEFT edge sits on rotation axis
    #
    # Plane width = plane_size
    #
    #base.location.x = plane_size / 2.0

    created = []

    for i in range(count):

        theta = math.pi * i / count

        obj = base.copy()
        obj.data = base.data

        collection.objects.link(obj)

        if axis == 'Y':

            obj.rotation_euler = (
                0.0,
                theta,
                0.0
            )

        elif axis == 'X':

            obj.rotation_euler = (
                theta,
                0.0,
                0.0
            )

        elif axis == 'Z':

            obj.rotation_euler = (
                math.pi / 2.0,
                0.0,
                theta
            )

        created.append(obj)

    #
    # Hide template
    #
    base.hide_viewport = True
    base.hide_render = True

    return created


# --------------------------------------------------
# Main function
# --------------------------------------------------

def plot_density_star(
        image_path,
        count=20,
        plane_size=6.0):

    mat = create_density_material(image_path)

    #
    # Cylinder axis along Z
    #
    create_axisymmetric_sweep(
        mat,
        count=count,
        plane_size=plane_size,
        axis='Z',
        name='DensityZ'
    )

'''
    #
    # Cylinder axis along Y
    #
    create_axisymmetric_sweep(
        mat,
        count=count,
        plane_size=plane_size,
        axis='Y',
        name='DensityY'
    )

    #
    # Cylinder axis along X
    #
    create_axisymmetric_sweep(
        mat,
        count=count,
        plane_size=plane_size,
        axis='X',
        name='DensityX'
    )
'''