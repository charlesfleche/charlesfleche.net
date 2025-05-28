Title: ufbx, a single source Open Source C++ FBX loader
Description: And Blender 4.5 will have an ufbx based importer

The [FBX](https://en.wikipedia.org/wiki/FBX) is a proprietary 3D scene file format from Autodesk. It is ubiquitous in the industry, especially in games. Its many iterations makes it a format rather difficult to work with and its closed source prevents free software application like [Blender](https://blender.org) to directly link against the Autodesk libs: Blender's developpers had to reimplement parts of an FBX I/O themselves, with not great results.

Fortunately the [`ufbx`](https://github.com/ufbx/ufbx) seems to be [a rather capable FBX reader](https://aras-p.info/blog/2025/05/08/Blender-FBX-importer-via-ufbx/). No writer yet, but [Blender 4.5 will have a new ufbx based importer](https://projects.blender.org/blender/blender/pulls/132406).
