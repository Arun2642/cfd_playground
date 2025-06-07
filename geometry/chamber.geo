
SetFactory("OpenCASCADE");
Box(1) = {0,0,0, 30.0, 20.0, 20.0};

Cylinder(2) = {4,10,2,  0,0,18.0, 1.5875};
Cylinder(3) = {26,10,20.0,  0,0,-2.0, 1.5875};

Box(4) = {10.0-0.055, 0, 0,
           0.11, 20.0, 20.0};

BooleanDifference{ Volume{1}; Delete; }{ Volume{2,3}; Delete; }
BooleanFuse       { Volume{1}; Delete; }{ Volume{4}; Delete; }

Physical Volume("fluid") = {1};
Physical Surface("inlet")  = Surface In BoundingBox{3.9,9.9,20, 4.1,10.1,20.1};
Physical Surface("outlet") = Surface In BoundingBox{25.9,9.9,17.9, 26.1,10.1,20.1};
Physical Surface("mesh")   = Surface In BoundingBox{9.94,-0.1,-0.1,
                                                     10.06,20.1,20.1};
Physical Surface("walls")  = Surface "*";

Characteristic Length{PointsOf{Volume{1};}} = 2.0;
Mesh.CharacteristicLengthExtend = 0;
