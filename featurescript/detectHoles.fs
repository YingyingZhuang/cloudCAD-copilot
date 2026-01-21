FeatureScript 2856;
import(path : "onshape/std/geometry.fs", version : "2856.0");
import(path : "onshape/std/evaluate.fs", version : "2856.0");
annotation { "Feature Type Name" : "Detect Holes"}
export const detectHoles = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        // Define the parameters of the feature type
        // User needs to choose a part(entity)
        annotation{"Name":"Select Part","Filter":EntityType.BODY}
        definition.part is Query;
    }
    {
        // Define the function's 
        // Select all the faces of this part
        var allFaces = qOwnedByBody(definition.part, EntityType.FACE);
        
        // Go through every face and check if it is a "hole" (cylindrical surface).
        var faces = evaluateQuery(context, allFaces);
        var holeCount = 0;
        
        for (var face in faces)
        {
            // Obtain the geometric properties of the face
            var surfaceDef = evSurfaceDefinition(context, { "face" : face });
            // Determine whether it is a cylinder
            if(surfaceDef.surfaceType == SurfaceType.CYLINDER)
            {
                // Obtain the radius and convert it to the diameter (in mm)
                var diameter = (surfaceDef.radius * 2) / millimeter;
                
                // Notice: this demo just simplely filtering: It ignores the outer cylindrical surfaces, and only consider the inner holes
                // Here, we assume that all cylindrical surfaces are the features we are concerned about
                println("Found Hole: Diameter " ~ roundToPrecision(diameter, 2) ~ " mm");
                holeCount = holeCount + 1;
            }
        }
        println("Analysis Complete: Found " ~ holeCount ~ " cylindrical features.");
    });
