Title: Shared SdfLayer and TfNotice
Description: Each stage sends its own change notice
Tags: openusd, usd, python

What happens if two [`UsdStage`](https://openusd.org/release/api/class_usd_stage.html) in the same processus share an [`SdfLayer`](https://openusd.org/release/api/class_sdf_layer.html) ? Turns out this does what is expected, with a twist:

1. Modifying a stage modifies the other
1. But the stage change notification is first sent to the last opened stage

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "usd-core>=26.5",
# ]
# ///

from pxr import Usd, UsdGeom, Sdf, Tf

stages = {}

def cb(notice, sender):
    print(f"{stages[sender]} changed")
l1 = Tf.Notice.Register(Usd.Notice.StageContentsChanged, cb, None)

sa = Usd.Stage.CreateInMemory()
stages[sa] = "StageA"

sb = Usd.Stage.Open(sa.GetRootLayer())
stages[sb] = "StageB"

print("Adding a prim to StageA")
sa.DefinePrim("/AddedFromStageA")

print("Adding a prim to StageB")
sb.DefinePrim("/AddedFromStageB")
```

```
Adding a prim to StageA
StageB changed
StageA changed
Adding a prim to StageB
StageB changed
StageA changed
```

