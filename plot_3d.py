# blender -b -P plot_3d.py -t 20

import bpy
import os
import importlib.util
import numpy as np
import sys
import re
import scipy

# Blender does not always add the script directory to its module search path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wave_eta import prepare_wave, wave_height, calc_Ylm, MODES
from time_bar import time_node_group
from mathutils import Vector, Matrix
#from shader_grid_solidlightblue import shader_twoblue_3

# ---------------------------------------------------------
# Dynamic module loader (CLI safe)
# ---------------------------------------------------------
def load_module(module_name, filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(current_dir, filename)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module
import bpy
import numpy as np

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def ensure_emission_material(name="GWTraceMaterial",
                             color=(1.0, 1.0, 1.0, 1.0),
                             strength=4.0):
    if name in bpy.data.materials:
        mat = bpy.data.materials[name]
        return mat

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.blend_method = 'OPAQUE'
    mat.shadow_method = 'OPAQUE'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    emission.location = (0, 0)

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (200, 0)

    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return mat


def create_or_update_polyline(name, points, bevel_depth=0.12, material=None):
    """
    points: list of (x, y, z)
    """
    if name in bpy.data.objects:
        obj = bpy.data.objects[name]
        curve = obj.data

        while curve.splines:
            curve.splines.remove(curve.splines[0])
    else:
        curve = bpy.data.curves.new(name=name, type='CURVE')
        curve.dimensions = '3D'
        curve.resolution_u = 12
        obj = bpy.data.objects.new(name, curve)
        bpy.context.collection.objects.link(obj)

    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)

    for i, (x, y, z) in enumerate(points):
        spline.points[i].co = (x, y, z, 1.0)

    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 6
    curve.fill_mode = 'FULL'

    if material is not None:
        if len(curve.materials) == 0:
            curve.materials.append(material)
        else:
            curve.materials[0] = material

    return obj


def plot_GW_trace(
    wave_file,
    current_time,
    r_max,
    width_frac=0.45,
    height_frac=0.18,
    y_frac=-0.78,
    x_frac=-0.90,
    z0=0.2,
    t_window=None,
    n_samples=500
):
    """
    Draw a 1D h_+(t_ret) trace in the scene, like an inset.
    """

    mass = float(os.environ.get("WAVE_M_ADM", "1.00071"))
    policy = os.environ.get("WAVE_RESTART_POLICY", "latest")
    data, tret, _ = prepare_wave(wave_file, mass, policy)
    harmonics = np.array([calc_Ylm(ell, m, np.pi/2, 0).real for ell, m in MODES])
    hplus = data.eta @ harmonics

    if t_window is None:
        tmin = tret.min()
        tmax = min(current_time, tret.max())
    else:
        tmax = current_time
        tmin = max(tret.min(), current_time - t_window)

    if tmax <= tmin:
        return

    ts = np.linspace(tmin, tmax, n_samples)
    hs = np.interp(ts, tret, hplus, left=0.0, right=0.0)

    hmax = np.max(np.abs(hplus))
    if hmax == 0:
        hmax = 1.0

    width = width_frac * r_max
    height = height_frac * r_max

    x0 = x_frac * r_max
    y0 = y_frac * r_max

    # waveform points
    pts = []
    for t, h in zip(ts, hs):
        x = x0 + width * (t - tmin) / (tmax - tmin)
        y = y0
        z = z0 + height * (h / hmax)
        pts.append((x, y, z))

    trace_mat = ensure_emission_material(
        name="GWTraceMaterial",
        color=(1.0, 1.0, 1.0, 1.0),
        strength=5.0
    )

    axis_mat = ensure_emission_material(
        name="GWAxisMaterial",
        color=(0.9, 0.9, 0.9, 1.0),
        strength=2.5
    )

    # waveform line
    create_or_update_polyline(
        "GWTrace",
        pts,
        bevel_depth=0.06,
        material=trace_mat
    )

    # horizontal axis
    create_or_update_polyline(
        "GWTraceAxisX",
        [(x0, y0, z0), (x0 + width, y0, z0)],
        bevel_depth=0.03,
        material=axis_mat
    )

    # vertical axis
    create_or_update_polyline(
        "GWTraceAxisY",
        [(x0, y0, z0 - 0.5 * height), (x0, y0, z0 + 0.5 * height)],
        bevel_depth=0.03,
        material=axis_mat
    )

    # current-time marker (right edge if using moving window)
    xcur = x0 + width
    create_or_update_polyline(
        "GWTraceMarker",
        [(xcur, y0, z0 - 0.5 * height), (xcur, y0, z0 + 0.5 * height)],
        bevel_depth=0.02,
        material=axis_mat
    )
def plot_GW(
    wave_file,
    NR,
    NPHI,
    hole_radius,
    r_max,
    height_scale,
    time_per_frame,
    current_time
):
    """
    Plot (or update) the gravitational wave height map for the
    current Blender frame.

    Parameters
    ----------
    wave_file : str
        Path to wave extraction file.
    NR : int
        Number of radial samples.
    NPHI : int
        Number of angular samples.
    hole_radius : float
        Inner radius.
    r_max : float
        Outer radius.
    height_scale : float
        Vertical scale factor.
    time_per_frame : float
        Physical time represented by one Blender frame.
    """

    # current_time is read from the same field-line header as the star frame.
    # time_per_frame is retained for CLI compatibility, not used as a clock.
    mass = float(os.environ.get("WAVE_M_ADM", "1.00071"))
    policy = os.environ.get("WAVE_RESTART_POLICY", "latest")
    if NR < 2 or NPHI < 3 or not (0 <= hole_radius < r_max):
        raise ValueError("GW mesh requires NR>=2, NPHI>=3, and 0<=hole_radius<r_max")
    if not np.isfinite(height_scale) or height_scale <= 0:
        raise ValueError("GW height_scale must be finite and positive")
    radii = np.linspace(hole_radius, r_max, NR)

    # test-cut-memory.md: for the cut view only 0 <= phi <= pi is generated
    # and the last sample is NOT joined back to the first, which leaves an
    # exposed radial boundary along y = 0 for the side camera to look at.
    cut = os.environ.get("WAVE_SIDEVIEW_CUT", "false").lower() == "true"
    if cut:
        phis = np.linspace(0, np.pi, NPHI)
    else:
        phis = np.linspace(0, 2 * np.pi, NPHI, endpoint=False)

    hp = wave_height(wave_file, current_time, radii, mass, policy)
    print(f"ETA waves: t={current_time:g}, M_ADM={mass:g}, "
          f"max |h+|={np.max(np.abs(hp)):.6e}, "
          f"display scale={height_scale:g}, cut={cut}")
    R, Phi = np.meshgrid(radii, phis, indexing="ij")
    X = R * np.cos(Phi)
    Y = R * np.sin(Phi)
    # wave_height already includes extraction normalization and 1/r decay.
    Z = height_scale * hp[:, None]

    verts = np.empty((NR * NPHI, 3), dtype=np.float32)
    verts[:, 0] = X.ravel()
    verts[:, 1] = Y.ravel()
    verts[:, 2] = np.broadcast_to(Z, X.shape).ravel()

    # --------------------------------------------------------
    # Faces
    # --------------------------------------------------------

    ir = np.arange(NR - 1)[:, None]
    # Angular wraparound faces disabled on the cut mesh: stop one sample
    # short so sample NPHI-1 is never joined to sample 0.
    ip = np.arange(NPHI - 1 if cut else NPHI)[None, :]
    ip2 = ip + 1 if cut else (ip + 1) % NPHI

    a = ir * NPHI + ip
    b = ir * NPHI + ip2
    c = (ir + 1) * NPHI + ip2
    d = (ir + 1) * NPHI + ip

    faces = np.stack((a, b, c, d), axis=-1).reshape(-1, 4)

    # --------------------------------------------------------
    # Create or update mesh
    # --------------------------------------------------------

    obj = bpy.data.objects.get("GWPlane")
    

    if obj is None:

        mesh = bpy.data.meshes.new("GWPlane")

        nverts = verts.shape[0]
        nfaces = faces.shape[0]

        mesh.vertices.add(nverts)
        mesh.loops.add(nfaces * 4)
        mesh.polygons.add(nfaces)

        mesh.vertices.foreach_set("co", verts.ravel())
        mesh.loops.foreach_set(
            "vertex_index",
            faces.astype(np.int32).ravel(),
        )
        mesh.polygons.foreach_set(
            "loop_start",
            np.arange(0, nfaces * 4, 4, dtype=np.int32),
        )
        mesh.polygons.foreach_set(
            "loop_total",
            np.full(nfaces, 4, dtype=np.int32),
        )

        mesh.update()

        obj = bpy.data.objects.new("GWPlane", mesh)
        bpy.context.collection.objects.link(obj)

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_smooth()

        # --------------------------------------------------------
        # Create material
        # --------------------------------------------------------
        mat = create_gw_material()

        obj = bpy.data.objects["GWPlane"]

        obj.data.materials.clear()
        obj.data.materials.append(mat)

    else:

        mesh = obj.data
        mesh.vertices.foreach_set("co", verts.ravel())
        mesh.update()

    return obj


def read_time_from_fieldline(field_path):

    with open(field_path, "r") as f:

        for line in f:

            if "coord time" in line:

                # Example:
                # # Data for OS initial data initial data at coord time 11.326918
                # and central proper time 11.326918

                m = re.search(
                    r'coord time\s+([-+0-9.eE]+)',
                    line
                )

                if m is not None:
                    t = float(m.group(1))
                    return t

    raise ValueError(
        f"Could not find coord time in {field_path}"
    )

def load_horizon_data(horizon_path):

    horizon_dict = {}

    with open(horizon_path, "r") as f:

        for line in f:

            if line.startswith("#") or not line.strip():
                continue

            parts = line.split()

            t = float(parts[0])
            theta = float(parts[1])
            radius = float(parts[2])

            if t not in horizon_dict:
                horizon_dict[t] = [[], []]

            horizon_dict[t][0].append(theta)
            horizon_dict[t][1].append(radius)

    for t in horizon_dict:

        theta = np.array(horizon_dict[t][0])
        radius = np.array(horizon_dict[t][1])

        # A restart rewinds to its checkpoint and re-evolves the stretch the
        # previous segment had already covered, appending a second copy of the
        # same surface for those times. Left as-is, theta runs 0..pi/2 and then
        # jumps back to 0, so create_bh's surface of revolution folds back
        # through itself. Sort by theta and keep the last (resumed-run) entry.
        order = np.lexsort((np.arange(len(theta)), theta))
        theta = theta[order]
        radius = radius[order]

        keep = np.concatenate([np.diff(theta) > 0, [True]])
        theta = theta[keep]
        radius = radius[keep]

        horizon_dict[t] = (theta, radius)

    return horizon_dict


def find_matching_horizon(current_time,
                          horizon_dict,
                          tol=0.2):

    if len(horizon_dict) == 0:
        return None

    times = np.array(sorted(horizon_dict.keys()))

    # No apparent horizon exists before the first recorded surface.
    if current_time < times[0]:
        print(f"No horizon yet (first horizon is at t={times[0]})")
        return None

    # Keep the final known surface if rendering extends beyond the data file.
    if current_time >= times[-1]:
        print(f"Using final horizon at t={times[-1]}")
        return horizon_dict[times[-1]]

    upper_idx = np.searchsorted(times, current_time, side="left")
    upper_time = times[upper_idx]

    if np.isclose(current_time, upper_time, rtol=0.0, atol=1e-10):
        print(f"Using horizon at t={upper_time}")
        return horizon_dict[upper_time]

    lower_time = times[upper_idx - 1]
    lower_theta, lower_radius = horizon_dict[lower_time]
    upper_theta, upper_radius = horizon_dict[upper_time]

    # Usually both surfaces share a theta grid. If not, first put them on
    # their common angular samples and then interpolate through time.
    if (len(lower_theta) == len(upper_theta)
            and np.allclose(lower_theta, upper_theta)):
        theta = lower_theta
        radius0 = lower_radius
        radius1 = upper_radius
    else:
        theta_min = max(lower_theta.min(), upper_theta.min())
        theta_max = min(lower_theta.max(), upper_theta.max())
        theta = np.unique(np.concatenate([
            lower_theta[(lower_theta >= theta_min) & (lower_theta <= theta_max)],
            upper_theta[(upper_theta >= theta_min) & (upper_theta <= theta_max)]
        ]))
        radius0 = np.interp(theta, lower_theta, lower_radius)
        radius1 = np.interp(theta, upper_theta, upper_radius)

    weight = (current_time - lower_time) / (upper_time - lower_time)
    radius = radius0 + weight * (radius1 - radius0)

    print(
        f"Interpolating horizon between t={lower_time} and "
        f"t={upper_time} (weight={weight:.3f})"
    )

    return theta, radius


def create_bh(theta, radius):

    nphi = 128

    phi = np.linspace(0, 2*np.pi, nphi, endpoint=False)

    verts = []
    faces = []

    ntheta = len(theta)

    # vertices
    for i in range(ntheta):

        r = radius[i]
        th = theta[i]

        s = np.sin(th)
        c = np.cos(th)

        for ph in phi:

            x = r*s*np.cos(ph)
            y = r*s*np.sin(ph)
            z = r*c

            verts.append((x, y, z))

    # faces
    for i in range(ntheta-1):

        for j in range(nphi):

            j2 = (j+1) % nphi

            a = i*nphi + j
            b = i*nphi + j2
            c = (i+1)*nphi + j2
            d = (i+1)*nphi + j

            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new("BlackHole")

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("BlackHole", mesh)

    bpy.context.collection.objects.link(obj)

    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.shade_smooth()

    # black material
    mat = bpy.data.materials.new("BHMaterial")
    mat.use_nodes = True

    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Emission Strength"].default_value = 0.0

    bsdf.inputs["Base Color"].default_value = (0,0,0,1)
    bsdf.inputs["Roughness"].default_value = 1.0

    obj.data.materials.append(mat)

    return obj


def create_gw_shader_material(name="GWMaterial"):
    """Wave-mesh shader ported from blender-gw's shader_twoblue_3.

    Reference: /data/yuhengguo/bhdisk_sol_32/blender-gw/lib/shader_grid_solidlightblue.py
    (function ``shader_twoblue_3``), as applied in ``lib/plot_single.py``.

    Structure, node for node:

      TexCoord.Object -> Mapping(loc=(0.7,0,0), rot=(0,pi/2,0), scale=(1,1,gz))
                      -> Gradient(LINEAR) -> ColorRamp   [height -> colour]
      ColorRamp -> Principled.Base Color and Principled.Emission Color
      TexCoord.Object -> Mapping(identity) -> Brick -> MixShader.Fac
      MixShader: Fac=1 (brick body, white)  -> Principled   [solid]
                 Fac=0 (mortar line, black) -> unconnected  [transparent]

    So the *sheet* is opaque (Alpha 0.95) and only the grid lines are
    see-through; the old create_brick_material() made the whole sheet
    translucent at Alpha 0.5, which is why the backdrop washed it out.

    Knobs (defaults reproduce the reference):
      GW_GRID_SCALE   brick Scale. The reference uses 0.125 over a +/-200
                      M_sun mesh (~4 M_sun cells); our mesh is +/-220.
      GW_GRAD_ZSCALE  Mapping z-scale feeding the gradient (reference 0.02).
                      Gradient Fac = 0.7 + GW_GRAD_ZSCALE * z_local, so with
                      WAVE_HEIGHT_SCALE=5e5 the peak |h+|=2.7e-5 swings the
                      ramp over ~0.43..0.97 -- the reference's dynamic range.
      GW_ALPHA        Principled Alpha (reference 0.95).
      GW_EMISSION     Emission Strength (reference leaves the 1.0 default,
                      which is what makes the sheet read as lit, not glassy).
    """
    grid_scale = float(os.environ.get("GW_GRID_SCALE", "0.125"))
    grad_zscale = float(os.environ.get("GW_GRAD_ZSCALE", "0.02"))
    alpha = float(os.environ.get("GW_ALPHA", "0.75"))
    emission = float(os.environ.get("GW_EMISSION", "0.0"))

    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    # --- Principled BSDF -------------------------------------------------
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Principled BSDF"
    bsdf.location = (663.3, 166.8)
    bsdf.width = 240.0
    bsdf.distribution = 'MULTI_GGX'
    bsdf.subsurface_method = 'RANDOM_WALK'
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["IOR"].default_value = 1.5
    bsdf.inputs["Alpha"].default_value = alpha
    if "Diffuse Roughness" in bsdf.inputs:
        bsdf.inputs["Diffuse Roughness"].default_value = 0.0
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = emission

    # --- Output ----------------------------------------------------------
    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = "Material Output"
    output.location = (1843.4, 226.0)
    output.is_active_output = True
    output.target = 'ALL'

    # --- Brick texture (grid lines) --------------------------------------
    brick = nodes.new("ShaderNodeTexBrick")
    brick.name = "Brick Texture"
    brick.location = (1007.6, -217.4)
    brick.width = 150.0
    brick.offset = 0.0
    brick.offset_frequency = 2
    brick.squash = 1.0
    brick.squash_frequency = 2
    brick.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
    brick.inputs["Color2"].default_value = (1.0, 1.0, 1.0, 1.0)
    brick.inputs["Mortar"].default_value = (0.0, 0.0, 0.0, 1.0)
    brick.inputs["Scale"].default_value = grid_scale
    brick.inputs["Mortar Size"].default_value = 0.014999999664723873
    brick.inputs["Mortar Smooth"].default_value = 1.0
    brick.inputs["Bias"].default_value = 0.0
    brick.inputs["Brick Width"].default_value = 0.5
    brick.inputs["Row Height"].default_value = 0.5

    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Mix Shader"
    mix.location = (1614.9, 93.1)

    mapping_brick = nodes.new("ShaderNodeMapping")
    mapping_brick.name = "Mapping.002"
    mapping_brick.location = (776.8, -331.1)
    mapping_brick.vector_type = 'POINT'
    mapping_brick.inputs["Location"].default_value = (0.0, 0.0, 0.0)
    mapping_brick.inputs["Rotation"].default_value = (0.0, 0.0, 0.0)
    mapping_brick.inputs["Scale"].default_value = (1.0, 1.0, 1.0)

    texco_brick = nodes.new("ShaderNodeTexCoord")
    texco_brick.name = "Texture Coordinate.002"
    texco_brick.location = (552.7, -380.0)
    texco_brick.from_instancer = False

    # --- Height -> colour gradient ---------------------------------------
    mapping_grad = nodes.new("ShaderNodeMapping")
    mapping_grad.name = "Mapping"
    mapping_grad.location = (-185.2, 506.7)
    mapping_grad.vector_type = 'POINT'
    mapping_grad.inputs["Location"].default_value = (0.6999999284744263, 0.0, 0.0)
    mapping_grad.inputs["Rotation"].default_value = (0.0, 1.5707999467849731, 0.0)
    mapping_grad.inputs["Scale"].default_value = (1.0, 1.0, grad_zscale)

    texco_grad = nodes.new("ShaderNodeTexCoord")
    texco_grad.name = "Texture Coordinate"
    texco_grad.location = (-365.2, 506.7)
    texco_grad.from_instancer = False

    gradient = nodes.new("ShaderNodeTexGradient")
    gradient.name = "Gradient Texture"
    gradient.location = (6.7, 414.6)
    gradient.gradient_type = 'LINEAR'

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Color Ramp"
    ramp.location = (230.5, 379.5)
    ramp.width = 240.0
    ramp.color_ramp.color_mode = 'RGB'
    ramp.color_ramp.hue_interpolation = 'NEAR'
    ramp.color_ramp.interpolation = 'LINEAR'
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[0])
    e0 = ramp.color_ramp.elements[0]
    e0.position = 0.0
    e0.alpha = 1.0
    e0.color = (0.019999999552965164, 0.019999999552965164,
                0.08399999886751175, 1.0)
    e1 = ramp.color_ramp.elements.new(0.9954545497894287)
    e1.alpha = 1.0
    e1.color = (0.2624173164367676, 0.7011075019836426, 1.0, 1.0)

    # --- Links ------------------------------------------------------------
    links.new(mapping_brick.outputs["Vector"], brick.inputs["Vector"])
    links.new(brick.outputs["Color"], mix.inputs[0])            # Fac
    links.new(bsdf.outputs["BSDF"], mix.inputs[2])              # 2nd shader
    links.new(texco_brick.outputs["Object"], mapping_brick.inputs["Vector"])
    links.new(texco_grad.outputs["Object"], mapping_grad.inputs["Vector"])
    links.new(mapping_grad.outputs["Vector"], gradient.inputs["Vector"])
    links.new(gradient.outputs["Color"], ramp.inputs["Fac"])

    # GW_COLOR_MODE=flat drops the height-driven colour variation: the ramp
    # chain is left in place but bypassed by a constant RGB node, so the
    # sheet is one colour regardless of z. The default is the ramp colour at
    # Fac = 0.7, i.e. the value an undisturbed sheet (z = 0) takes in the
    # gradient mode, so a flat render matches the movie's resting tone.
    if os.environ.get("GW_COLOR_MODE", "gradient").lower() == "flat":
        flat = [float(c) for c in os.environ.get(
            "GW_FLAT_COLOR", "0.1905,0.4990,0.7281").split(",")]
        rgb = nodes.new("ShaderNodeRGB")
        rgb.name = "Flat Colour"
        rgb.location = (230.5, 150.0)
        rgb.outputs[0].default_value = (flat[0], flat[1], flat[2], 1.0)
        colour_source = rgb.outputs["Color"]
        print(f"GW colour: flat {tuple(flat)}")
    else:
        colour_source = ramp.outputs["Color"]
        print("GW colour: height gradient")

    links.new(colour_source, bsdf.inputs["Base Color"])
    if "Emission Color" in bsdf.inputs:
        links.new(colour_source, bsdf.inputs["Emission Color"])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])

    print(f"GW shader (twoblue_3 port): grid_scale={grid_scale:g}, "
          f"grad_zscale={grad_zscale:g}, alpha={alpha:g}, emission={emission:g}")
    return mat


def create_gw_material():
    """Pick the wave-mesh material. GW_SHADER=brick restores the old look."""
    if os.environ.get("GW_SHADER", "twoblue3").lower() == "brick":
        return create_brick_material()
    return create_gw_shader_material()


def create_brick_material(
    name="GWMaterial",
    color1=(0.24, 0.41, 0.40, 1.0),
    color2=(0.24, 0.41, 0.40, 1.0)
):
    # Reuse material if it already exists
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    nodes.clear()

    # --------------------------------------------------
    # Nodes
    # --------------------------------------------------

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (250, 0)

    brick = nodes.new("ShaderNodeTexBrick")
    brick.location = (-100, 0)

    # --------------------------------------------------
    # Brick Texture settings
    # --------------------------------------------------

    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 150
    brick.inputs["Mortar Size"].default_value = 0.02
    brick.inputs["Mortar Smooth"].default_value = 0.1
    brick.inputs["Brick Width"].default_value = 1.0
    brick.inputs["Row Height"].default_value = 1.0   # "Brick Height"

    brick.inputs["Color1"].default_value = color1
    brick.inputs["Color2"].default_value = color2

    # --------------------------------------------------
    # Principled BSDF settings
    # --------------------------------------------------

    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Alpha"].default_value = 0.5

    # --------------------------------------------------
    # Links
    # --------------------------------------------------

    links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    return mat

# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------
def abs_path(root_dir, path):
    return os.path.abspath(os.path.join(root_dir, path))


def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_render(render_path, plot_wave=False):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    #scene.render.engine = "BLENDER_EEVEE"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(os.environ.get("RENDER_SAMPLES", "64"))
    scene.render.resolution_percentage = int(os.environ.get("RENDER_PERCENT", "100"))
    if "RENDER_DENOISE" in os.environ:
        scene.cycles.use_denoising = os.environ["RENDER_DENOISE"].lower() == "true"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = render_path
    if plot_wave:
        #scene.render.resolution_x = 1200
        #scene.render.resolution_y = 1200
        print("Plotting wave, setting rendering resolution to default")
    else:
        scene.render.resolution_x = 1200
        scene.render.resolution_y = 1200
    # Reference blender-gw never sets this, so it renders under Blender 5.0's
    # default AgX. Ours forces Standard. VIEW_TRANSFORM=AgX matches the reference.
    bpy.context.scene.view_settings.view_transform = os.environ.get(
        "VIEW_TRANSFORM", "Standard")
    bpy.context.scene.cycles.transparent_max_bounces = 100

def setup_camera(plot_wave=False):
    cam_data = bpy.data.cameras.new(name="Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    # test-cut-memory.md camera: orthographic, on the negative-y side,
    # looking straight along the exposed cut toward positive y.
    if os.environ.get("WAVE_CAMERA", "").lower() == "side_cut":
        az = np.deg2rad(float(os.environ.get("WAVE_SIDEVIEW_AZIMUTH", "-90")))
        el = np.deg2rad(float(os.environ.get("WAVE_SIDEVIEW_ELEVATION", "0")))
        dist = float(os.environ.get("WAVE_SIDEVIEW_DISTANCE", "320.624"))
        target = Vector((
            float(os.environ.get("WAVE_SIDEVIEW_TARGET_X", "0")),
            float(os.environ.get("WAVE_SIDEVIEW_TARGET_Y", "20")),
            float(os.environ.get("WAVE_SIDEVIEW_TARGET_Z", "-2")),
        ))
        offset = Vector((
            dist * np.cos(el) * np.cos(az),
            dist * np.cos(el) * np.sin(az),
            dist * np.sin(el),
        ))
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = float(
            os.environ.get("WAVE_SIDEVIEW_ORTHO_SCALE", "90"))
        cam.data.clip_end = 5000
        cam.location = target + offset
        look_at(cam, target)
        print(f"side_cut camera: az={np.rad2deg(az):g} el={np.rad2deg(el):g} "
              f"dist={dist:g} target={tuple(target)} "
              f"ortho_scale={cam.data.ortho_scale:g}")
        return cam

    if plot_wave:
        cam.data.type = 'PERSP'

        cam.location = (69, -71.5, 37.3)
        cam.rotation_euler = (np.deg2rad(70), np.deg2rad(0), np.deg2rad(45))
        cam.data.lens = 45
        cam.data.clip_end = 5000

    else:
        cam.data.type = 'PERSP'

        cam.location = (69, -71.5, 37.3)
        cam.rotation_euler = (np.deg2rad(70), np.deg2rad(0), np.deg2rad(45))

        cam.data.lens=45
        cam.data.clip_end = 5000

    return cam
def setup_light():
    # Light 1
    light_data = bpy.data.lights.new("Light1", type='POINT')
    light_data.use_nodes = True
    
    nodes = light_data.node_tree.nodes
    links = light_data.node_tree.links
    
    nodes.clear()
    
    output = nodes.new(type="ShaderNodeOutputLight")
    emission = nodes.new(type="ShaderNodeEmission")
    falloff = nodes.new(type="ShaderNodeLightFalloff")
    
    emission.inputs["Strength"].default_value = 4000
    
    # Use Linear falloff (slower decay)
    links.new(falloff.outputs["Linear"], emission.inputs["Strength"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    
    light = bpy.data.objects.new("Light1", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (4, 10.5, 2)

    # Light 2
    light_data_2 = bpy.data.lights.new("Light2", type='POINT')
    light_2 = bpy.data.objects.new("Light2", light_data_2)
    bpy.context.collection.objects.link(light_2)
    light_2.location = (0, -10, 6)
    light_data_2.energy = 4000
    light_data_2.exposure = 2

    # ---- Light just for GW plane ----
    # Normal sun
    sun_data = bpy.data.lights.new("Sun", type='SUN')
    # blender-gw lights its wave mesh with a single SUN at energy 2.5.
    sun_data.energy = float(os.environ.get("GW_SUN_ENERGY", "4"))

    sun = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun)

    sun.rotation_euler = (
        np.deg2rad(1.9),
        np.deg2rad(48.0),
        np.deg2rad(55.5),
    )

    # GW-only sun
    gw_sun_data = bpy.data.lights.new("GW_Sun", type='SUN')
    gw_sun_data.energy = float(os.environ.get("GW_SUN2_ENERGY", "0.3"))

    gw_sun = bpy.data.objects.new("GW_Sun", gw_sun_data)
    bpy.context.collection.objects.link(gw_sun)

    gw_sun.rotation_euler = (
        np.deg2rad(1.9),
        np.deg2rad(48.0),
        np.deg2rad(55.5),
    )
    # ---- Light just for GW plane ----

    gw = bpy.data.objects.get("GWPlane")
    if gw is not None:
        bpy.ops.object.select_all(action='DESELECT')
        sun.select_set(True)
        gw.select_set(True)

        bpy.context.view_layer.objects.active = sun

        bpy.ops.object.light_linking_receivers_link(
            link_state='INCLUDE'
        )

        # GW sun affects only GW
        link_light(gw_sun, gw, 'INCLUDE')

        # All other lights ignore GW
        link_light(light,   gw, 'EXCLUDE')
        link_light(light_2, gw, 'EXCLUDE')
        link_light(sun,     gw, 'EXCLUDE')

def link_light(light_obj, receiver, state):
    bpy.ops.object.select_all(action='DESELECT')

    light_obj.select_set(True)
    receiver.select_set(True)

    bpy.context.view_layer.objects.active = light_obj

    bpy.ops.object.light_linking_receivers_link(
        link_state=state
    )

def create_time_label(camera, current_time):
    """t/M label, top-right, ported from blender-gw.

    Node group is lib/time_bar.py verbatim (copied in as time_bar.py): a
    "t/M = " string joined to a Value-to-String whose Decimals input is 0,
    so the label shows whole numbers only -- "t/M = 0", not "t/M = 0.00".
    GW_TIME_DECIMALS raises that if the integer label sits still too long.

    blender-gw feeds the node frame_number*PSI4_DT/M_ADM. We already read the
    coordinate time from the field-line header, so we feed t/M directly.

    Placement follows plot_single.py: parent to the camera, sit in camera
    space at depth 100. Their numbers are for a 50mm lens; ours is 45mm, so
    the frame half-extents differ (40.0 x 22.5 vs 36.0 x 20.25) and the
    position and size are rescaled to keep the same corner and the same
    ~10% of frame height.
    """
    if os.environ.get("GW_TIME_LABEL", "true").lower() != "true":
        return None

    mass = float(os.environ.get("WAVE_M_ADM", "1.00071"))
    t_over_m = current_time / mass

    group = time_node_group()
    for node in group.nodes:
        if node.name == "Value to String":
            node.inputs[0].default_value = t_over_m
            node.inputs[1].default_value = int(
                os.environ.get("GW_TIME_DECIMALS", "0"))
            break

    mesh = bpy.data.meshes.new("TimeMesh")
    obj = bpy.data.objects.new("TimeText", mesh)
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers.new("TimePlot", 'NODES')
    mod.node_group = group

    # blender-gw's label material is Base Color (0,0,1) with Emission
    # Strength 1 -- but its Emission Color stays black, so nothing glows.
    # Their rendered frames show the glyphs at sRGB (198,200,212), so use
    # that as an emissive colour here: legible over both the bright sheet
    # and the dark hole, which a lit-only material is not.
    colour = [float(c) for c in os.environ.get(
        "GW_TIME_COLOR", "0.573,0.585,0.665").split(",")]
    mat = bpy.data.materials.new("TimeLabelMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*colour, 1.0)
    emit.inputs["Strength"].default_value = 1.0
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(emit.outputs["Emission"], out.inputs["Surface"])

    set_mat = group.nodes.new("GeometryNodeSetMaterial")
    set_mat.inputs["Material"].default_value = mat
    group_output = next(n for n in group.nodes if n.type == "GROUP_OUTPUT")
    last_socket = group_output.inputs["Geometry"].links[0].from_socket
    group.links.new(last_socket, set_mat.inputs["Geometry"])
    group.links.new(set_mat.outputs["Geometry"], group_output.inputs["Geometry"])

    depth = 100.0
    lens = camera.data.lens
    half_w = depth * (camera.data.sensor_width / 2.0) / lens
    half_h = half_w * 9.0 / 16.0
    obj.parent = camera
    obj.matrix_parent_inverse = Matrix.Identity(4)
    # 23.25/36.0 and 15.75/20.25: plot_single.py's fractions of the frame.
    obj.location = Vector((0.6458 * half_w, 0.7778 * half_h, -depth))
    obj.rotation_euler = (0.0, 0.0, 0.0)
    scale = 0.12 * (half_h / 20.25)
    obj.scale = (scale, scale, scale)
    obj.visible_shadow = False

    print(f"Time label: t/M = {t_over_m:g} "
          f"(t={current_time:g}, M_ADM={mass:g}), "
          f"decimals={os.environ.get('GW_TIME_DECIMALS', '0')}")
    return obj


def create_backdrop_plane():
    """Bright plane under the wave mesh, ported from blender-gw's white_plane.blend.

    That file holds a single large plane whose material is an RGB node wired
    straight into Surface, i.e. a flat self-lit colour unaffected by the scene
    lights. It shows through the mesh cutout as a bright halo and lifts the
    translucent wave shader, which is why the reference renders read as a solid
    surface instead of a dark one. Off unless GW_BACKDROP=true.
    """
    if os.environ.get("GW_BACKDROP", "true").lower() != "true":
        return None

    z = float(os.environ.get("GW_BACKDROP_Z", "-100"))
    size = float(os.environ.get("GW_BACKDROP_SIZE", "6000"))
    colour = [float(c) for c in os.environ.get(
        "GW_BACKDROP_COLOR", "0.35,0.38,0.42").split(",")]

    # A floor at z is edge-on to the side_cut camera (elevation 0), so it
    # contributes nothing and the world colour shows instead. blender-gw's
    # own white_plane.blend is rotated (1.571, 0, 0) -- a vertical wall --
    # so "wall" is the reference orientation; "auto" picks it for side_cut.
    orient = os.environ.get("GW_BACKDROP_ORIENT", "auto").lower()
    if orient == "auto":
        orient = ("wall" if os.environ.get("WAVE_CAMERA", "").lower()
                  == "side_cut" else "floor")

    if orient == "wall":
        wall_y = float(os.environ.get("GW_BACKDROP_WALL_Y", "500"))
        bpy.ops.mesh.primitive_plane_add(size=size,
                                         location=(0.0, wall_y, 0.0),
                                         rotation=(np.pi / 2, 0.0, 0.0))
    else:
        bpy.ops.mesh.primitive_plane_add(size=size, location=(0.0, 0.0, z))

    plane = bpy.context.active_object
    plane.name = "GWBackdrop"

    mat = bpy.data.materials.new("GWBackdropMaterial")
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    rgb = nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = (colour[0], colour[1], colour[2], 1.0)
    rgb.location = (-200, 0)

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (100, 0)

    links.new(rgb.outputs["Color"], output.inputs["Surface"])

    plane.data.materials.append(mat)
    plane.visible_shadow = False

    print(f"GW backdrop: orient={orient}, z={z:g}, size={size:g}, "
          f"colour={tuple(colour)}")

    return plane


def setup_world_background():
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world

    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    # blender-gw uses (0.006, 0.006, 0.051): near-black, so the sun alone lights
    # the mesh. WORLD_COLOR overrides ours without touching the default look.
    world_colour = [float(c) for c in os.environ.get(
        "WORLD_COLOR", "0.03,0.05,0.15").split(",")]
    bg.inputs["Color"].default_value = (*world_colour, 1.0)
    bg.inputs["Strength"].default_value = 1.0


# ---------------------------------------------------------
# Geometry Node Object
# ---------------------------------------------------------
def create_object_with_modifier(node_group, ply_path, radius, value):
    mesh = bpy.data.meshes.new("BaseMesh")
    obj = bpy.data.objects.new("FieldObject", mesh)
    #obj.rotation_euler = (0, np.pi / 2, np.pi * 35/180)
    obj.rotation_euler = (np.pi / 2, 0, np.pi * 0/180) #(np.pi / 2, 0, np.pi * 45/180)
    bpy.context.collection.objects.link(obj)

    mod = obj.modifiers.new("GeometryNodes", "NODES")
    mod.node_group = node_group

    for item in mod.node_group.interface.items_tree:
        if item.name == "Path":
            mod[item.identifier] = ply_path
        if item.name == "Radius":
            mod[item.identifier] = radius
        if item.name == "Value":
            mod[item.identifier] = value

    return obj


# ---------------------------------------------------------
# Main Plot Function
# ---------------------------------------------------------
def plot_3d(
    root_dir,
    ply_path,
    density_file,
    render_path,
    wave_file=None,
    save_blender=False,
    save_blender_path=None,
    radius=0.02,
    value=2,
    field_line=None,
    horizon_file=None,
    plot_wave=False,
    hole_radius=0.0,
    height_scale=1.0,
    time_per_frame=1.0,
    r_max=10.0,
    NR=100,
    NPHI=100
):

    clean_scene()

    ply_abs = abs_path(root_dir, ply_path)
    render_abs = abs_path(root_dir, render_path)

    current_time = read_time_from_fieldline(field_line)

    # --- Read current time ---

    print(f"Current frame time = {current_time}")

    horizon_dict = load_horizon_data(horizon_file)

    horizon_data = find_matching_horizon(
        current_time,
        horizon_dict,
        tol=0.2
    )

    if horizon_data is not None:

        theta_h, radius_h = horizon_data

        # Add north pole if necessary
        if theta_h[0] > 1e-6:
            theta_h = np.insert(theta_h, 0, 0.0)
            radius_h = np.insert(radius_h, 0, radius_h[0])

        # Reflect
        theta_h = np.concatenate([
            theta_h,
            np.pi - theta_h[-2::-1]
        ])

        radius_h = np.concatenate([
            radius_h,
            radius_h[-2::-1]
        ])

        # Only append south pole if reflection didn't already produce it
        if theta_h[-1] < np.pi - 1e-6:
            theta_h = np.append(theta_h, np.pi)
            radius_h = np.append(radius_h, radius_h[-1])

        create_bh(theta_h, radius_h)

    else:

        print("No black hole present.")



    # Load external modules
    geo_module = load_module("geo_node", "geo_node.py")
    density_module = load_module("plot_density", "plot_density.py")

    # Build node trees
    node_tree_names = {}

    nodegroup = geo_module.node_group_for_ply(node_tree_names)
    node_tree_names[geo_module.node_group_for_ply] = nodegroup.name

    field_line = geo_module.field_line_1_node_group(node_tree_names)
    node_tree_names[geo_module.field_line_1_node_group] = field_line.name



    # Only resolve density if it exists
    if density_file is not None:
        density_abs = abs_path(root_dir, density_file)
    else:
        density_abs = None

    os.makedirs(os.path.dirname(render_abs), exist_ok=True)

    gw = None

    if plot_wave:
        if not wave_file:
            raise ValueError("plot_wave=True requires a wave_file")
        gw = plot_GW(
            wave_file=wave_file,
            NR=NR,
            NPHI=NPHI,
            hole_radius=hole_radius,
            r_max=r_max,
            height_scale=height_scale,
            time_per_frame=time_per_frame,
            current_time=current_time
        )

        
    # Setup scene
    camera = setup_camera(plot_wave)
    setup_light()
    setup_world_background()
    create_backdrop_plane()
    create_time_label(camera, current_time)
    setup_render(render_abs, plot_wave)

    # Create density sphere
    if density_abs is not None:
        density_module.plot_density_star(density_abs, 50)
    else:
        print("No density file provided. Skipping density plot.")


    # Create geometry-node object
    if os.environ.get("WAVE_HIDE_FIELD_LINES", "false").lower() == "true":
        print("Field lines hidden (WAVE_HIDE_FIELD_LINES)")
    else:
        field_obj = create_object_with_modifier(
        node_group=field_line,
        ply_path=ply_abs,
        radius=radius,
        value=int(value),
        )

        field_obj.visible_shadow = False

    # Render
    bpy.ops.render.render(write_still=True)
    print("Render saved to:", render_abs)

    # Optional: save blend file
    if save_blender and save_blender_path:
        blend_abs = abs_path(root_dir, save_blender_path)
        os.makedirs(os.path.dirname(blend_abs), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend_abs)
        print("Blend file saved to:", blend_abs)


# ---------------------------------------------------------
# CLI Execution
# ---------------------------------------------------------

if __name__ == "__main__":
    # Blender adds its own args; custom args are after "--"
    if "--" not in sys.argv:
        print("No arguments provided. Make sure to use '--'")
        sys.exit(1)

    argv = sys.argv[sys.argv.index("--") + 1:]

    if len(argv) != 19:
        print(f"Received {len(argv)} arguments, expected 19. Arguments: {argv}")
        sys.exit(1)

    field_line = argv[0]
    root_dir = argv[1]
    output_dir = argv[2]
    horizon_file = argv[3]
    ply_subdir = argv[4]
    save_blender = argv[5].lower() == "true"
    radius = float(argv[6])
    value = float(argv[7])
    blend_subdir = argv[8]
    render_subdir = argv[9]
    density_file = None if argv[10].lower() in {"none", "null", ""} else argv[10]
    wave_file = argv[11] 
    plot_wave = argv[12].lower() == "true"  
    hole_radius = float(argv[13]) 
    height_scale = float(argv[14])
    time_per_frame = float(argv[15])
    r_max = float(argv[16])
    NR = int(argv[17])
    NPHI = int(argv[18])

    base = os.path.basename(field_line)
    raw_num = base.split("_")[-1]

    field_num = int(raw_num)

# Field file timestep: 000010
    frame_num = f"{field_num:08d}"

# PLY file timestep: 00000100
# PLY file timestep: 004420
    ply_num = f"{field_num:06d}"

    ply_path = os.path.join(ply_subdir, f"field_lines_{ply_num}.ply")
    render_path = os.path.join(output_dir, render_subdir, f"render_{frame_num}.png")
    blend_path = os.path.join(output_dir, blend_subdir, f"scene_{frame_num}.blend")
    os.makedirs(os.path.dirname(render_path), exist_ok=True)
    os.makedirs(os.path.dirname(blend_path), exist_ok=True)

    # ✅ Call plot_3d
    plot_3d(
        root_dir=root_dir,
        ply_path=ply_path,
        density_file=density_file,
        render_path=render_path,
        wave_file=wave_file,
        save_blender=save_blender,
        save_blender_path=blend_path,
        radius=radius,
        value=value,
        field_line=field_line,
        horizon_file=horizon_file,
        plot_wave=plot_wave,
        hole_radius=hole_radius,
        height_scale=height_scale,
        time_per_frame=time_per_frame,
        r_max=r_max,
        NR=NR,
        NPHI=NPHI
)


