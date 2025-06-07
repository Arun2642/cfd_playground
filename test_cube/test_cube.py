#!/usr/bin/env python3
"""
Self-contained unit-test for a 5 mm cube CFD case using OpenFOAM-9:
1. Generates case directories and dictionaries (with proper FoamFile headers).
2. Runs blockMesh and simpleFoam.
3. Samples centerline velocity.
4. Compares against analytical Poiseuille within 3%.
"""
import subprocess
import pathlib
import shutil
import textwrap
import numpy as np

# Helper to run shell commands
def run(cmd, cwd=None):
    print(f">>> {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd)

# Set up paths
test_dir = pathlib.Path(__file__).parent.resolve()
case_dir = test_dir / "case"

# Remove existing case and prepare directories
def prepare_case():
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "system").mkdir(parents=True)
    (case_dir / "constant").mkdir()
    (case_dir / "0").mkdir()

# FoamFile header template
def foam_header(obj_name):
    return textwrap.dedent(f"""
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      {obj_name};
}}
// * * * * * * * * * * * * * * * * * * * * * //
""")

# Write all dictionaries
def write_dictionaries():
    # system/blockMeshDict
    blockMeshDict = textwrap.dedent("""
convertToMeters 0.001;
vertices (
    (0 0 0)
    (5 0 0)
    (5 5 0)
    (0 5 0)
    (0 0 5)
    (5 0 5)
    (5 5 5)
    (0 5 5)
);
blocks (
    hex (0 1 2 3 4 5 6 7) (20 20 20) simpleGrading (1 1 1)
);
boundary (
    inlet  { type patch; faces ((0 3 7 4)); }
    outlet { type patch; faces ((1 2 6 5)); }
    walls  { type wall;  faces (
        (0 1 5 4)
        (3 2 6 7)
        (0 1 2 3)
        (4 5 6 7)
    ); }
);
""")
    (case_dir / "system" / "blockMeshDict").write_text(
        foam_header("blockMeshDict") + blockMeshDict
    )

    # system/fvSchemes
    fvSchemes = textwrap.dedent("""
ddtSchemes
{
    default         steadyState;
}
gradSchemes
{
    default         Gauss linear;
}
divSchemes
{
    default         none;
    div(phi,U)      Gauss linear;
}
laplacianSchemes
{
    default         Gauss linear corrected;
}
interpolationSchemes
{
    default         linear;
}
snGradSchemes
{
    default         corrected;
}
""")
    (case_dir / "system" / "fvSchemes").write_text(
        foam_header("fvSchemes") + fvSchemes
    )

    # system/fvSolution
    fvSolution = textwrap.dedent("""
solvers
{
    p
    {
        solver          PCG;
        tolerance       1e-06;
        relTol          0;
    }
    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-06;
        relTol          0;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;
}

relaxationFactors
{
    fields
    {
        p               0.3;
    }
    equations
    {
        U               0.7;
    }
}
""")
    (case_dir / "system" / "fvSolution").write_text(
        foam_header("fvSolution") + fvSolution
    )

        # system/controlDict
    controlDict = textwrap.dedent("""
application     simpleFoam;
startFrom       startTime;
startTime       0;
endTime         200;
deltaT          1;
writeControl    timeStep;
writeInterval   200;
purgeWrite      0;
""")
    (case_dir / "system" / "controlDict").write_text(
        foam_header("controlDict") + controlDict
    )

    # constant/transportProperties
    transportProperties = textwrap.dedent("""
transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] 1e-6;
""")
    (case_dir / "constant" / "transportProperties").write_text(
        foam_header("transportProperties") + transportProperties
    )

        # constant/momentumTransport (required by this build)
    (case_dir / "constant" / "momentumTransport").write_text(
        foam_header("momentumTransport") + "simulationType laminar;\n"
    )

    # 0/U
    U_field = textwrap.dedent("""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0.001 0 0);
boundaryField
{
    inlet  { type fixedValue; value uniform (0.001 0 0); }
    outlet { type zeroGradient; }
    walls  { type noSlip; }
}
""")
    (case_dir / "0" / "U").write_text(
        foam_header("U") + U_field
    )

    # 0/p
    p_field = textwrap.dedent("""
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet  { type zeroGradient; }
    outlet { type fixedValue; value uniform 0; }
    walls  { type zeroGradient; }
}
""")
    (case_dir / "0" / "p").write_text(
        foam_header("p") + p_field
    )

    # system/sampleDict
    sampleDict = textwrap.dedent("""
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      sampleDict;
}

interpolationScheme cellPoint;
sets ( centerLine uniform (0 2.5 2.5) (5 2.5 2.5) 100 );
fields ( U );
""")
    (case_dir / "system" / "sampleDict").write_text(sampleDict)

# Main execution
def main():
    prepare_case()
    write_dictionaries()

    # 1) Mesh & solve
    run(["blockMesh", "-case", str(case_dir)])
    run(["simpleFoam", "-case", str(case_dir)])

    # 2) Sample centreline
    run(["postProcess", "-case", str(case_dir), "-func", "sample"])

    # 3) Load sampled data and compare
    data_file = case_dir / "postProcessing" / "sets" / "200" / "centerLine_U.xy"
    data = np.loadtxt(data_file)
    x = data[:,0]
    u_num = data[:,2]  # Ux component

    # Analytical parabolic profile
    u_max = u_num.max()
    u_analytic = u_max * (1 - (x/5)**2)
    err = np.linalg.norm(u_num - u_analytic) / np.linalg.norm(u_analytic)
    print(f"relative L2 error = {err:.3%}")
    assert err < 0.03, "Velocity deviates >3% from Poiseuille"
    print("✔ unit test passed")

if __name__ == '__main__':
    main()
