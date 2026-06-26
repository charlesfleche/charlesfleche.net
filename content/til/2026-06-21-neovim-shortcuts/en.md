Title: neovim shortcuts
Description: My list of neovim shortcuts, as I learn them
Tags:

I'm trying to learn [neovim](https://neovim.io/) more thoroughly. It's heavily shortcut based that I need to learn little by little. Here is a list to help me memorize them:

# Neovim Shortcuts Summary

## Editing
- `D` — Delete to end of line
- `d$` — Same as `D`
- `3D` — Delete to end of line, 3 lines
- `d0` — Delete backward to the start of the line
- `dw` — Delete word forward
- `db` — Delete word backward
- `dB` — Delete word backward (incl. punctuation)
- `$dB` — Delete last word of the line
- `ggVG` — Select entire buffer
- `"+y` — Yank selection to system clipboard
- `ggVG"+y` — Select + copy whole buffer to clipboard

## Windows / Splits
- `Ctrl-w v` — Vertical split
- `Ctrl-w s` — Horizontal split
- `:vsp filename` — Vertical split with new file
- `:sp filename` — Horizontal split with new file
- `:q` / `Ctrl-w q` — Close current split
- `Ctrl-w c` — Close current split
- `:close` — Close current window (not last one)
- `:only` / `Ctrl-w o` — Close all other splits

## Tabs
- `:tabnew file` — Open file in new tab
- `gt` / `gT` — Next / previous tab
- `:tabclose` — Close current tab
- `:tabs` — List all tabs
- `2gt` — Jump to tab 2

## LSP / Diagnostics
- `gd` — Go to definition
- `gD` — Go to declaration
- `gi` — Go to implementation
- `gr` — Go to references
- `K` — Hover docs
- `<leader>rn` — Rename symbol
- `<leader>ca` — Code action
- `<C-k>` — Signature help
- `<leader>e` (custom) — Open diagnostic float
- `<F5>` — DAP: continue
- `<F10>` — DAP: step over
- `<F11>` — DAP: step into
- `<leader>b` (custom) — Toggle breakpoint
- `<leader>x` (custom, trouble.nvim) — Toggle diagnostics panel
- `<leader>sS` — Show workspace symbols
- `<leader>ss` — Show document symbols

## File browser
- `<leader>ff` — Find files
- `<leader>fg` — Live grep (requires rgrep)
- `<leader>fb` — List buffers
- `<leader>fh` — Help tags
- `<leader>fo` — Recently opened files

## Command-line / Ex Commands
- `:%s/.../.../g` — Substitute over whole buffer
- `:g/^  /d` — Delete all lines starting with two spaces
- `:g/^  /` — Preview matches without deleting
- `:g/^  /normal dd` — Delete matches via global+normal
- `:make` — Run build (via `makeprg`)
- `:copen` — Open quickfix list
- `:checkhealth nvim-treesitter` — Check treesitter health
- `:checkhealth provider` — Check clipboard provider

## Misc
- `:qa` — Quit vim and all buffers
- `<leader>` — Custom prefix key, default `\`, commonly remapped to `Space` via `vim.g.mapleader = " "`
