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
        // Array for storing structured results
        var holeResults = []; 
        var recommendations = [];
        
        println("--------------------------------");
        println("Analyzing Geometry & Generating Recommendations:");

        
        for (var face in faces)
        {
            /*1.Obtain the geometric properties of the face 
            Notice: this demo just simplely filtering: It ignores the outer cylindrical surfaces, and only consider the inner holes.Here, we assume that all cylindrical surfaces are the features we are concerned about */
            var surfaceDef = evSurfaceDefinition(context, { "face" : face });
            
            // 2.Determine whether it is a cylinder
            if(surfaceDef.surfaceType == SurfaceType.CYLINDER)
            {
                // Obtain the radius and convert it to the diameter(in mm)
                var diameter = (surfaceDef.radius * 2) / millimeter;
                
                // Simple depth assumption (using plate thickness in the MVP stage)
                var depth = 35; 
                
                // Simply assume that only those smaller than 50mm can be considered as holes.
                if (diameter < 50) {
                    
                    // Classification Logic
                    // Rules: Less than 8.5mm is considered as the pin hole (8mm), and more than 8.5mm is regarded as the screw through hole (9mm).
                    
                    var holeType = diameter < 8.5 ? "Dowel Pin" : "Screw Clearance";
                    var standard = diameter < 8.5 ? "ISO 8734" : "ISO 4762";
                    
                    // RAG
                    var recLength = 0;
                    var recSize = "";
                    
                    if (holeType == "Dowel Pin") {
                        
                        // Rule: Length of the pin = Plate thickness + 5mm
                        recLength = depth + 5;
                        recSize = roundToPrecision(diameter, 1) ~ "mm";
                    } else {
                        // Rule: Length of screw = Board thickness * 0.7 (rounded to the nearest whole number)
                        recLength = round(depth * 0.7);
                        recSize = "M" ~ round(diameter - 1); // 9mm -> M8
                    }

                    // 5. Save the results
                    holeResults = append(holeResults, {
                        "diameter" : diameter,
                        "type" : holeType
                    });
                
                println("Found:" ~ roundToPrecision(diameter, 2) ~  "mm -> Type: " ~ holeType);
                    println("Recommendation: " ~ standard ~ " " ~ recSize ~ " x " ~ recLength ~ "mm");
                }
            }
        }
        
        println("--------------------------------");
        println("Summary: Processed " ~ size(holeResults) ~ " features.");
        println("--------------------------------");
    });