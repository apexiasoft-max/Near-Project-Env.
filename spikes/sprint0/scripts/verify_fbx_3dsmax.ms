-- Sprint 0 disposable compatibility check for normalized FBX artifacts.
-- Runs in 3ds Max Batch and writes a machine-readable TSV report.

global outputPath = "C:/Users/Ariya Rayan/Documents/Near Project Environment/spikes/sprint0/artifacts/benchmark-results/3dsmax-fbx-compatibility.tsv"
global samples = #(
    #("RUN-S0-001", "C:/Users/Ariya Rayan/Documents/Near Project Environment/spikes/sprint0/artifacts/normalized-fbx/RUN-S0-001/RUN-S0-001-building-48m.fbx", 48.0),
    #("RUN-S0-002", "C:/Users/Ariya Rayan/Documents/Near Project Environment/spikes/sprint0/artifacts/normalized-fbx/RUN-S0-002/RUN-S0-002-building-60m.fbx", 60.0),
    #("RUN-S0-003", "C:/Users/Ariya Rayan/Documents/Near Project Environment/spikes/sprint0/artifacts/normalized-fbx/RUN-S0-003/RUN-S0-003-building-6m.fbx", 6.0)
)

fn inspectSample sample outFile = (
    local runId = sample[1]
    local inputPath = sample[2]
    local targetHeightM = sample[3]
    local status = "pass"
    local message = ""
    local objectCount = 0
    local vertexCount = 0
    local faceCount = 0
    local sizeX = 0.0
    local sizeY = 0.0
    local sizeZ = 0.0

    resetMaxFile #noPrompt
    units.SystemType = #Meters
    units.SystemScale = 1.0

    try (
        importFile inputPath #noPrompt using:FBXIMP
        local meshNodes = for node in geometry where canConvertTo node Editable_Mesh collect node
        objectCount = meshNodes.count
        if objectCount == 0 then throw "No importable geometry nodes"

        local bbMin = [1e9, 1e9, 1e9]
        local bbMax = [-1e9, -1e9, -1e9]
        for node in meshNodes do (
            local converted = snapshotAsMesh node
            vertexCount += getNumVerts converted
            faceCount += getNumFaces converted
            delete converted
            bbMin.x = amin #(bbMin.x, node.min.x)
            bbMin.y = amin #(bbMin.y, node.min.y)
            bbMin.z = amin #(bbMin.z, node.min.z)
            bbMax.x = amax #(bbMax.x, node.max.x)
            bbMax.y = amax #(bbMax.y, node.max.y)
            bbMax.z = amax #(bbMax.z, node.max.z)
        )
        sizeX = bbMax.x - bbMin.x
        sizeY = bbMax.y - bbMin.y
        sizeZ = bbMax.z - bbMin.z
        if (abs (sizeZ - targetHeightM)) > 0.02 then (
            status = "fail"
            message = "Imported height differs from target by more than 0.02m"
        )
    ) catch (
        status = "fail"
        message = getCurrentException()
    )

    format "%\t%\t%\t%\t%\t%\t%\t%\t%\n" runId status objectCount vertexCount faceCount sizeX sizeY sizeZ message to:outFile
)

global outFile = createFile outputPath
format "run_id\tstatus\tobject_count\tvertex_count\tface_count\tsize_x_m\tsize_y_m\tsize_z_m\tmessage\n" to:outFile
for sample in samples do inspectSample sample outFile
close outFile
quitMax #noPrompt
