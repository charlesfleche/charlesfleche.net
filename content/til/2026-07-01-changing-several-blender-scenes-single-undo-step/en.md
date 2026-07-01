Title: Changing several Blender scenes, single undo step
Description: What is pushed on the Undo stack when a script modifies several scenes at once ?
Tags: blender, python

Text editors like [VSCodium](https://vscodium.com/) have an undo stack per opened text file. One can modify file A, switch to file B, edit it, get back to file A and trigger an undo: only the active file A will be reversed, not file B.

Blender can also modify several scenes within the same session, albeit with two major differences:

1. a single document contains all scenes
2. the user can edit a single scene at once

The second point is naturally enforced by the fact that switching the active scene is an undoable command by itself: select a scene, CTRL+Z, and we're back to the previous scene. In VSCodium selecting an active text editor panel goes into another undo stack, the one that allows to navigate through the documents, but not into the documents edition stack.

So I wanted to test my assumptions for a few situations regarding Python scripts and undo stack:

1. Are all python changes revertable in a single undo ?
1. Are the ops and data APIs handled differently ?
1. What happens when a script modifies several scenes ?

TL;DR: python scripts changes are always revertable as a single undo step.

```python
# Single scene, ops API

import bpy

for i in range(3):
    bpy.ops.mesh.primitive_cube_add(size=.5, location=(0, i, 0))

# RESULT: a single undo step removes all three cubes
```

```python
# Single scene, data API

for i in range(3):
    obj = bpy.data.objects.new(name=f"empty_{i}", object_data=None)
    bpy.context.scene.collection.objects.link(obj)
#
# RESULT: a single undo step removes all three objects
```

```python
# Several scenes, data API

def new(scene, name):
    for i in range(3):
        obj = bpy.data.objects.new(
            name=f"{scene.name}_{name}_{i}",
            object_data=None
        )
        scene.collection.objects.link(obj)

scene_a = bpy.data.scenes["SceneA"]
scene_b = bpy.data.scenes["SceneB"]

new(scene_a, "batch1")
new(scene_b, "batch2")
new(scene_b, "batch3")
new(scene_a, "batch4")

# RESULT: a single undo step removes all the objects created in the two scenes
```

