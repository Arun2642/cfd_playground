#!/usr/bin/env python3
"""
1. Generate chamber.geo from parameters
2. Call gmsh -3 to produce chamber.stl
3. Show a Matplotlib preview (blue = inlet tube, green = full mesh plate,
   red = outlet) so you can eyeball the geometry before meshing in OpenFOAM.
"""
import subprocess, pathlib, textwrap, numpy as np, matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# ---------- user‑tunable numbers (mm) --------------------
params = dict(
    lx=30.0, ly=20.0, lz=20.0,
    tube_id=3.175, tube_len=18.0,
    mesh_x=10.0, mesh_thk=0.11,
    out_id=3.175, out_depth=2.0,
)

here = pathlib.Path(__file__).parent.resolve()
geo_path = here / "chamber.geo"
stl_path = here / "chamber.stl"

# ---------- write chamber.geo ----------------------------
geo_template = f"""
SetFactory("OpenCASCADE");
Box(1) = {{0,0,0, {params['lx']}, {params['ly']}, {params['lz']}}};

Cylinder(2) = {{4,10,2,  0,0,{params['tube_len']}, {params['tube_id']/2}}};
Cylinder(3) = {{26,10,{params['lz']},  0,0,-{params['out_depth']}, {params['out_id']/2}}};

Box(4) = {{{params['mesh_x']}-{params['mesh_thk']/2}, 0, 0,
           {params['mesh_thk']}, {params['ly']}, {params['lz']}}};

BooleanDifference{{ Volume{{1}}; Delete; }}{{ Volume{{2,3}}; Delete; }}
BooleanFuse       {{ Volume{{1}}; Delete; }}{{ Volume{{4}}; Delete; }}

Physical Volume("fluid") = {{1}};
Physical Surface("inlet")  = Surface In BoundingBox{{3.9,9.9,20, 4.1,10.1,20.1}};
Physical Surface("outlet") = Surface In BoundingBox{{25.9,9.9,17.9, 26.1,10.1,20.1}};
Physical Surface("mesh")   = Surface In BoundingBox{{{params['mesh_x']-0.06},-0.1,-0.1,
                                                     {params['mesh_x']+0.06},{params['ly']+0.1},{params['lz']+0.1}}};
Physical Surface("walls")  = Surface "*";

Characteristic Length{{PointsOf{{Volume{{1}};}}}} = 2.0;
Mesh.CharacteristicLengthExtend = 0;
"""
geo_path.write_text(textwrap.dedent(geo_template))

# ---------- call gmsh ------------------------------------
subprocess.check_call(["gmsh", "-3", "-format", "stl",
                       "-o", str(stl_path), str(geo_path)])

print(f"✓  STL written to {stl_path}")

# ---------- quick 3‑D preview -----------------------------
def cyl_faces(base, vec, r, n=48):
    # returns side faces for plotting
    z = vec/np.linalg.norm(vec)
    # find two perpendicular vectors
    x = np.cross([0,0,1], z) if abs(z[2])<0.99 else np.cross([0,1,0], z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    t = np.linspace(0, 2*np.pi, n, endpoint=False)
    c0 = np.array([base + r*(np.cos(th)*x + np.sin(th)*y) for th in t])
    c1 = c0 + vec
    return [[c0[i], c0[(i+1)%n], c1[(i+1)%n], c1[i]] for i in range(n)]

fig = plt.figure(figsize=(6,5))
ax = fig.add_subplot(111, projection='3d')
ax.set_box_aspect([params['lx'], params['ly'], params['lz']])

# chamber wireframe
for xs in [[0, params['lx']]]:
    for ys in [[0, params['ly']]]:
        ax.plot([xs[0], xs[1], xs[1], xs[0], xs[0]],
                [ys[0], ys[0], ys[1], ys[1], ys[0]],
                [0, 0, 0, 0, 0], color='k', alpha=0.3)
        ax.plot([xs[0], xs[1], xs[1], xs[0], xs[0]],
                [ys[0], ys[0], ys[1], ys[1], ys[0]],
                [params['lz']]*5, color='k', alpha=0.3)
for x in (0, params['lx']):
    for y in (0, params['ly']):
        ax.plot([x, x],[y, y],[0, params['lz']], color='k', alpha=0.3)

# inlet tube
faces = cyl_faces(np.array([4,10,2]), np.array([0,0, params['tube_len']]), params['tube_id']/2)
ax.add_collection3d(Poly3DCollection(faces, facecolor='skyblue', alpha=0.6))

# outlet tube
faces = cyl_faces(np.array([26,10,params['lz']]),
                  np.array([0,0,-params['out_depth']]), params['out_id']/2)
ax.add_collection3d(Poly3DCollection(faces, facecolor='salmon', alpha=0.6))

# mesh plate (draw both faces for visibility)
mx = params['mesh_x']; th = params['mesh_thk']; ly = params['ly']; lz = params['lz']
plate = [[mx-th/2, 0, 0],[mx+th/2, 0, 0],[mx+th/2, ly, 0],[mx-th/2, ly, 0],
         [mx-th/2, 0, lz],[mx+th/2, 0, lz],[mx+th/2, ly, lz],[mx-th/2, ly, lz]]
faces = [[plate[0],plate[1],plate[2],plate[3]],
         [plate[4],plate[5],plate[6],plate[7]]]
ax.add_collection3d(Poly3DCollection(faces, facecolor='forestgreen', alpha=0.4))

ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)'); ax.set_zlabel('z (mm)')
ax.set_title('Quick geometry preview'); plt.tight_layout(); plt.show()
