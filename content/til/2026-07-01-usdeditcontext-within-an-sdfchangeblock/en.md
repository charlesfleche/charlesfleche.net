Title: UsdEditContext within an SdfChangeBlock
Description: Is the notice still emitted ?
Tags: openusd, usd, python, code

No USD level changes should be made within an [`SdfChangeBlock`](https://openusd.org/release/api/class_sdf_change_block.html). I wanted to check if this still stands for "edition" that are purely at the USD level: as far as I know an changing a change edit target does not touch the Sdf API.

Turns out: [`StageEditTargetChanged`](https://openusd.org/release/api/class_usd_notice_1_1_stage_edit_target_changed.html) are still emitted without throwing exception within an `SdfChangeBlock`.

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "usd-core>=26.5",
# ]
# ///

from pxr import Usd, UsdGeom, Sdf, Tf

def cb(notice, sender):
    print(notice)

s = Usd.Stage.CreateInMemory()

l1 = Tf.Notice.Register(Usd.Notice.StageEditTargetChanged, cb, s)
l2 = Tf.Notice.Register(Sdf.Notice.LayersDidChange, cb, None)

print("@@@ No SdfChangeBlock")

with Usd.EditContext(s, s.GetSessionLayer()):
    s.DefinePrim("/A_in_session")

with Usd.EditContext(s, s.GetRootLayer()):
    s.DefinePrim("/A_in_rootlayer")

print("@@@ Within an SdfChangeBlock")

with Sdf.ChangeBlock():
    lay = s.GetSessionLayer()
    with Usd.EditContext(s, lay):
        p = Sdf.CreatePrimInLayer(lay, "/B_in_session")
        p.specifier = Sdf.SpecifierDef

    lay = s.GetRootLayer()
    with Usd.EditContext(s, lay):
        p = Sdf.CreatePrimInLayer(lay, "/B_in_rootlayer")
        p.specifier = Sdf.SpecifierDef
```

```
@@@ No SdfChangeBlock
<pxr.Usd.Notice.StageEditTargetChanged object at 0x7fc4a8b7e680>
<pxr.Sdf.Notice.LayersDidChange object at 0x7fc4a8b7e680>
<pxr.Usd.Notice.StageEditTargetChanged object at 0x7fc4a8b7e680>
<pxr.Sdf.Notice.LayersDidChange object at 0x7fc4a8b7e680>
@@@ Within an SdfChangeBlock
<pxr.Usd.Notice.StageEditTargetChanged object at 0x7fc4a8b7e680>
<pxr.Usd.Notice.StageEditTargetChanged object at 0x7fc4a8b7e680>
<pxr.Sdf.Notice.LayersDidChange object at 0x7fc4a8b7e5f0>
```
