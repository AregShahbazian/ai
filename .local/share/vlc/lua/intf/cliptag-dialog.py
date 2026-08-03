#!/usr/bin/env python3
"""Clip-tagger dialog helper, invoked by rotate_hotkey.lua (VLC lua intf).

Usage:  cliptag-dialog.py tags <absolute-clip-path>
        cliptag-dialog.py series [<absolute-clip-path>]
Env:    CLIPTAG_ROOT       clips root folder (holds tags.txt); optional — if
                           unset, the root is discovered by walking up from
                           the clip to the nearest cliptags.json (prints
                           NODB if none found)
        CLIPTAG_DB         json db file; optional, default <root>/cliptags.json
        CLIPTAG_AUTOCLOSE  test hook: auto-close the dialog after ~0.6s

Custom GTK3 dialogs (zenity 4 broke checklist keyboard handling), fully
keyboard-driven — typed characters accumulate in a background filter query,
no focused input field. Run with /usr/bin/python3 (pyenv lacks PyGObject).

tags mode:   check-list of <root>/tags.txt with the clip's current tags
             pre-checked. Tab-indented lines in tags.txt render as nested
             child tags (stored flat, indent is presentation + filtering:
             a query match keeps its subtree and ancestors visible).
             Lines starting with "#" are section labels — shown dim and
             unselectable; their group (deeper-indented rows, plus
             same-depth rows down to the next label) filters with them.
             Label rows carry a "+" button: prompts for a tag name and
             inserts it at the end of that label's group, rewriting
             tags.txt in place (works in both dialogs).
             Label-group members carry a "⠿" drag handle on the left:
             drag onto another row of the same group to reorder; the
             group's block order in tags.txt (sublines included) follows.
             Ungrouped tags are not reorderable.
             Every tag row carries "✏" (rename) and "🗑" (delete, with
             confirm) buttons — both rewrite tags.txt AND refactor all
             references in the db (clip tags, series tags); rename merges
             if the target name already exists (works in both dialogs).
             Series show as pinned "⚡ title" rows with a link/unlink
             button at the right (space does the same when the row is
             selected): link the series to the clip and check its tags,
             or, if it is the linked one, delink and uncheck its tags.
             While a series is linked, each tag row shows a "→⚡" button
             (ctrl+a = selected row) that pushes that tag's on/off state
             into the linked series without opening the series dialog.
series mode: CRUD editor for root-wide series (named tag templates):
             selector + new/rename/delete, and the same tag picker editing
             the selected series' tags.

Keys: type = filter, backspace = clear query, up/down = move, space =
toggle / apply series, enter = save, esc = cancel. Series mode also:
left/right = switch series (auto-saves), ctrl+n/r/d = new/rename/delete.

Prints one line for the lua side to show as OSD:
  tags:   SAVED: tag1, tag2 | CANCELLED
  series: DONE
(anything else = error, see stderr)

Db shape: { "clips":  { "<path relative to root>":
                          { "tags": [...], "series": "<title>",
                            "notes": "<free text>" } },
            "series": { "<title>": { "tags": [...] } } }
Clip notes: free-text area at the bottom of the tags dialog; tab moves
between it and the tag list, saved with enter (from the list).
A clip's "series" link (max 1) is set by applying a series in the tags
dialog; it survives tag edits, and follows series renames/deletes.
"""
import json
import os
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

HINT_PICKER = "type = filter · backspace = clear (hold = untoggle visible) · ↑↓ = move · space = toggle · enter = save · esc = cancel"
HINT_SERIES = "←→ = switch series · ctrl+n/r/d = new/rename/delete · " + HINT_PICKER


def load_db(db_path):
    if os.path.exists(db_path):
        with open(db_path) as f:
            return json.load(f)
    return {}


def save_db(db_path, db):
    tmp = db_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(db, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, db_path)


def load_options(root):
    """Return [(tag, depth), ...] from <root>/tags.txt; leading tabs (or
    4-space runs) nest a tag under the previous less-indented one."""
    try:
        with open(os.path.join(root, "tags.txt")) as f:
            return [(ln.strip(), _line_depth(ln)) for ln in f if ln.strip()]
    except FileNotFoundError:
        return []


def _line_depth(ln):
    ws = ln[:len(ln) - len(ln.lstrip())]
    return ws.count("\t") + len(ws.replace("\t", "")) // 4


def add_tag_to_label(root, label, depth, new_tag):
    """Insert new_tag at the end of the given label's group in tags.txt,
    matching the group's member indent style. Rewrites the file, keeping
    every other line (including blanks) verbatim. Returns True on success."""
    path = os.path.join(root, "tags.txt")
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return False
    li = next((i for i, ln in enumerate(lines)
               if ln.strip().startswith("#") and _line_depth(ln) == depth
               and ln.strip().lstrip("#").strip() == label), None)
    if li is None:
        return False
    nxt_depth = next((_line_depth(ln) for ln in lines[li + 1:] if ln.strip()), None)
    deep = nxt_depth is None or nxt_depth > depth
    member_depth = depth + 1 if deep else depth
    end = li  # insert right after the label when the group is empty
    for k in range(li + 1, len(lines)):
        ln = lines[k]
        if not ln.strip():
            continue  # blank lines don't end a group
        d = _line_depth(ln)
        if deep:
            if d <= depth:
                break
        elif d < depth or (ln.strip().startswith("#") and d <= depth):
            break
        if ln.strip() == new_tag:
            return True  # already in this group — nothing to do
        end = k
    lines.insert(end + 1, "\t" * member_depth + new_tag)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return True


def reorder_label_group(root, label, depth, ordered):
    """Rewrite the given label's group in tags.txt so its member blocks (a
    member line plus its deeper-indented sublines) follow `ordered`. Inner
    blank lines are dropped; everything outside the group is untouched."""
    path = os.path.join(root, "tags.txt")
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return False
    li = next((i for i, ln in enumerate(lines)
               if ln.strip().startswith("#") and _line_depth(ln) == depth
               and ln.strip().lstrip("#").strip() == label), None)
    if li is None:
        return False
    nxt_depth = next((_line_depth(ln) for ln in lines[li + 1:] if ln.strip()), None)
    deep = nxt_depth is None or nxt_depth > depth
    member_depth = depth + 1 if deep else depth
    blocks = {}
    current = None
    end = li
    for k in range(li + 1, len(lines)):
        ln = lines[k]
        if not ln.strip():
            continue  # blanks don't end a group (trailing ones stay outside)
        d = _line_depth(ln)
        if deep:
            if d <= depth:
                break
        elif d < depth or (ln.strip().startswith("#") and d <= depth):
            break
        if d == member_depth:
            current = ln.strip()
            blocks[current] = [ln]
        elif current is not None:
            blocks[current].append(ln)  # deeper subline moves with its member
        end = k
    if set(ordered) != set(blocks):
        return False  # stale view of the file — refuse to rewrite
    reordered = [ln for name in ordered for ln in blocks[name]]
    lines[li + 1:end + 1] = reordered
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return True


def parse_options(items):
    """Normalize [(name, depth)|name, ...] into entry dicts with kind
    ("label" for lines starting with #, else "tag") and indent ancestors."""
    entries = []
    stack = []
    for item in items:
        name, depth = item if isinstance(item, tuple) else (item, 0)
        depth = min(depth, len(stack))  # tolerate indent jumps
        stack = stack[:depth]
        kind = "label" if name.startswith("#") else "tag"
        if kind == "label":
            name = name.lstrip("#").strip()
        entries.append({"kind": kind, "name": name, "depth": depth,
                        "ancestors": list(stack)})
        stack.append(name)
    return entries


def segment_groups(entries):
    """Split entries into display groups that must never wrap apart:
    each label + its group (deeper-indented rows, or same-depth rows down
    to the next label), and each uninterrupted label-less run of tags."""
    groups = []
    run = None
    i = 0
    while i < len(entries):
        e = entries[i]
        if e["kind"] == "label":
            run = None
            grp = [e]
            d = e["depth"]
            nxt = entries[i + 1] if i + 1 < len(entries) else None
            deep = nxt is not None and nxt["depth"] > d
            i += 1
            while i < len(entries):
                x = entries[i]
                if deep:
                    if x["depth"] <= d:
                        break
                elif x["depth"] < d or (x["kind"] == "label" and x["depth"] <= d):
                    break
                grp.append(x)
                i += 1
            groups.append(grp)
        else:
            if run is None:
                run = []
                groups.append(run)
            run.append(e)
            i += 1
    return groups


def resolve_root(clip):
    """Return (root, db_path), or None if no root can be determined.

    Launcher env wins; otherwise walk up from the clip to the nearest
    cliptags.json — its folder is the root. So clips opened in plain VLC
    (no launcher) still store to the right root db.
    """
    root = os.environ.get("CLIPTAG_ROOT")
    if root:
        return root, os.environ.get("CLIPTAG_DB", os.path.join(root, "cliptags.json"))
    if not clip:
        return None
    d = os.path.dirname(os.path.abspath(clip))
    while True:
        db_path = os.path.join(d, "cliptags.json")
        if os.path.exists(db_path):
            return d, db_path
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def prompt_text(parent, title_text, default=""):
    dlg = Gtk.Dialog(title=title_text, transient_for=parent, modal=True)
    dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "OK", Gtk.ResponseType.OK)
    dlg.set_default_response(Gtk.ResponseType.OK)
    entry = Gtk.Entry(text=default)
    entry.set_activates_default(True)
    area = dlg.get_content_area()
    area.set_border_width(10)
    area.add(entry)
    dlg.show_all()
    resp = dlg.run()
    text = entry.get_text().strip()
    dlg.destroy()
    return text if resp == Gtk.ResponseType.OK and text else None


def confirm_text(parent, text):
    dlg = Gtk.MessageDialog(transient_for=parent, modal=True,
                            message_type=Gtk.MessageType.QUESTION,
                            buttons=Gtk.ButtonsType.YES_NO, text=text)
    resp = dlg.run()
    dlg.destroy()
    return resp == Gtk.ResponseType.YES


def _rename_in_list(lst, old, new):
    if old in lst:
        seen = set()
        lst[:] = [t for t in (new if t == old else t for t in lst)
                  if not (t in seen or seen.add(t))]


def rename_tag_everywhere(root, db, old, new):
    """Rename a tag in tags.txt (indent preserved) and every clip/series
    reference in the db. Merges (dedupes) if new already exists."""
    path = os.path.join(root, "tags.txt")
    try:
        with open(path) as f:
            lines = f.read().splitlines()
        for i, ln in enumerate(lines):
            if ln.strip() == old and not ln.strip().startswith("#"):
                lines[i] = ln[:len(ln) - len(ln.lstrip())] + new
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
    except FileNotFoundError:
        pass
    for c in db.get("clips", {}).values():
        _rename_in_list(c.get("tags", []), old, new)
    for s in db.get("series", {}).values():
        _rename_in_list(s.get("tags", []), old, new)


def delete_tag_everywhere(root, db, tag):
    """Drop a tag's line(s) from tags.txt and every clip/series reference."""
    path = os.path.join(root, "tags.txt")
    try:
        with open(path) as f:
            lines = f.read().splitlines()
        lines = [ln for ln in lines
                 if ln.strip() != tag or ln.strip().startswith("#")]
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
    except FileNotFoundError:
        pass
    for c in db.get("clips", {}).values():
        if tag in c.get("tags", []):
            c["tags"].remove(tag)
    for s in db.get("series", {}).values():
        if tag in s.get("tags", []):
            s["tags"].remove(tag)


def relink_series(db, old, new):
    """Follow a series rename (new=title) or delete (new=None) on clip links."""
    for clip in db.get("clips", {}).values():
        if clip.get("series") == old:
            if new is None:
                clip.pop("series")
            else:
                clip["series"] = new


class TagPicker:
    """Filterable check-list widget; all keys arrive via handle_key()."""

    _compact_css = None  # shared provider for padding-free row buttons

    def __init__(self, tags, checked, series=None, linked_series=None, on_apply=None,
                 on_add_tag=None, on_rename_tag=None, on_delete_tag=None):
        self.query = ""
        self.on_apply = on_apply  # callback(tag, active): per-row "apply to series"
        self.on_add_tag = on_add_tag  # callback(label, depth): "+" on label rows
        self.on_rename_tag = on_rename_tag  # callback(tag): "✏" on tag rows
        self.on_delete_tag = on_delete_tag  # callback(tag): "🗑" on tag rows
        self.on_link_changed = None  # notified when the series link toggles
        self.on_reorder = None  # callback(label, depth, ordered): drag-reorder
        self._drag_row = None
        self.applied_series = None  # series applied this session (max 1, last wins)
        self.linked_series = linked_series  # series already stored on the clip
        self._bs_start = self._bs_last = None  # backspace press/hold tracking
        self.query_lbl = Gtk.Label(label="", xalign=0)
        self.clear_btn = Gtk.Button(label="Clear")
        self.clear_btn.set_can_focus(False)
        self.clear_btn.set_no_show_all(True)  # visible only while filtering
        self.clear_btn.connect("clicked", lambda *a: self.set_query(""))
        clear_all_btn = Gtk.Button(label="Clear all")
        clear_all_btn.set_can_focus(False)
        clear_all_btn.set_tooltip_text("untoggle all visible tags (ctrl+u or hold backspace)")
        clear_all_btn.connect("clicked", lambda *a: self.clear_visible())
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.pack_start(self.query_lbl, True, True, 0)
        bar.pack_start(self.clear_btn, False, False, 0)
        bar.pack_start(clear_all_btn, False, False, 0)

        # column-fill layout (flex-col + wrap): GROUP boxes — each a ListBox
        # of rows that must stay together (a label + its tags, a label-less
        # run, or all series) — stack downward at natural height and wrap
        # into a new column when the next group wouldn't fit the viewport
        # height. GTK3's vertical FlowBox can't do this (it gives every
        # child its own column), so _relayout() packs an HBox of VBoxes.
        self.columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        self._columns = []
        self._last_h = 0
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_vexpand(True)
        self.scroller.add(self.columns_box)
        self.scroller.connect("size-allocate", self._on_scroller_alloc)

        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.widget.pack_start(bar, False, False, 0)
        self.widget.pack_start(self.scroller, True, True, 0)
        self.reload(tags, checked, series)

    def reload(self, tags, checked, series=None):
        for group in getattr(self, "_groups", []):
            group.container.destroy()
        for col in self._columns:
            col.destroy()
        self._columns = []
        self._rows = []
        self._groups = []
        self._selected = None
        self._series_group = None
        self._extra_group = None  # lazily holds tags added at runtime
        if series:
            self._series_group = self._new_group(scroll_max=self.SERIES_MAX_HEIGHT)
            for title in sorted(series):
                self._add_series_row(title, series[title].get("tags", []))
        for grp in segment_groups(parse_options(tags)):
            group = self._new_group()
            label_row = None
            for e in grp:
                if e["kind"] == "label":
                    label_row = self._add_label_row(group, e["name"], e["depth"],
                                                    e["ancestors"])
                else:
                    row = self._add_tag_row(e["name"], e["name"] in checked,
                                            e["depth"], e["ancestors"], group,
                                            group_label=(label_row.tag, label_row.depth)
                                            if label_row is not None else None)
                    if label_row is not None:
                        # group members filter together with their label
                        label_row.descendants.append(e["name"].lower())
                        if label_row.tag.lower() not in row.ancestors:
                            row.ancestors.append(label_row.tag.lower())
        # indent-based descendants (labels included, so a deeper label ends
        # the shallower tag's subtree), keeping subtrees filtering together
        rows = [r for r in self._rows if r.kind != "series"]
        for i, row in enumerate(rows):
            if row.kind == "label":
                continue  # label groups were linked above; labels only bound subtrees
            for below in rows[i + 1:]:
                if below.depth <= row.depth:
                    break
                row.descendants.append(below.tag.lower())
        self.set_query("")

    SERIES_MAX_HEIGHT = 200  # ≈7 rows; the series group scrolls beyond this

    def _new_group(self, scroll_max=None):
        group = Gtk.ListBox()
        group.set_selection_mode(Gtk.SelectionMode.SINGLE)
        group.set_filter_func(lambda row, *a: self._matches(row))
        group.connect("row-selected", self._on_row_selected)
        group.set_activate_on_single_click(False)  # single click only selects
        group.set_halign(Gtk.Align.CENTER)  # centered in its column slot
        group.set_valign(Gtk.Align.START)   # never taller than it needs
        group.container = group
        if scroll_max:
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.set_propagate_natural_height(True)  # natural height up to the cap
            sw.set_max_content_height(scroll_max)
            sw.add(group)
            group.show()
            group.container = sw
        self._groups.append(group)
        return group

    def _on_scroller_alloc(self, widget, alloc):
        if alloc.height != self._last_h:
            self._last_h = alloc.height
            GLib.idle_add(self._relayout)  # never repack inside an allocation

    def _relayout(self):
        """Greedy column fill: stack visible groups top-down at natural
        height, wrapping to a fresh column when the viewport height is
        exceeded. Re-run on resize, filtering, and content changes."""
        h_avail = self.scroller.get_allocated_height()
        if h_avail <= 1:
            return False  # not allocated yet; size-allocate will call again
        spacing = 10
        for col in self._columns:
            for child in col.get_children():
                col.remove(child)  # keep the groups alive for repacking
            self.columns_box.remove(col)
        self._columns = []
        col, used = None, 0
        for group in self._groups:
            if not group.container.get_visible():
                continue
            h = group.container.get_preferred_height().natural_height
            if col is None or (used > 0 and used + h > h_avail):
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
                col.set_valign(Gtk.Align.START)
                self.columns_box.pack_start(col, False, False, 0)
                col.show()
                self._columns.append(col)
                used = 0
            col.pack_start(group.container, False, False, 0)
            used += h + spacing
        return False  # one-shot when used via idle_add

    def _add_row(self, child, kind, tag, group, rows_index=None):
        row = Gtk.ListBoxRow()
        row.add(child)
        row.set_can_focus(False)
        row.kind, row.tag = kind, tag
        row.depth, row.ancestors, row.descendants = 0, [], []
        group.add(row)
        row.show_all()
        if rows_index is None:
            self._rows.append(row)
        else:
            self._rows.insert(rows_index, row)
        return row

    def _on_row_selected(self, group, row):
        # mouse clicks land here; keep at most one selected row across groups
        if row is None or getattr(self, "_sel_guard", False):
            return
        self._selected = row
        self._sel_guard = True
        for g in self._groups:
            if g is not group:
                g.unselect_all()
        self._sel_guard = False

    def _do_select(self, row):
        self._sel_guard = True
        for g in self._groups:
            g.unselect_all()
        if row is not None:
            row.get_parent().select_row(row)
        self._selected = row
        self._sel_guard = False

    def selected_row(self):
        return self._selected

    def _series_label(self, title):
        linked = self.applied_series or self.linked_series
        return "⚡ " + title + (" ✓" if title == linked else "")

    def _add_series_row(self, title, tags, rows_index=None):
        lbl = Gtk.Label(label=self._series_label(title), xalign=0)
        lbl.get_style_context().add_class("dim-label")
        toggle_btn = Gtk.Button()
        self._compact(toggle_btn)
        toggle_btn.set_tooltip_text(
            "link this series to the clip and check its tags / unlink and uncheck them")
        child = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        child.pack_start(lbl, True, True, 0)
        child.pack_end(toggle_btn, False, False, 0)
        row = self._add_row(child, "series", title, self._series_group, rows_index)
        row.series_tags = list(tags)
        row.lbl = lbl
        row.toggle_btn = toggle_btn
        toggle_btn.set_label(self._series_btn_label(title))
        toggle_btn.connect("clicked", lambda *a: self._toggle_series(row))
        return row

    def _series_btn_label(self, title):
        linked = self.applied_series or self.linked_series
        return "✕" if title == linked else "🔗"

    def _compact(self, btn):
        # strip the theme's button padding so the row keeps its height
        if TagPicker._compact_css is None:
            TagPicker._compact_css = Gtk.CssProvider()
            TagPicker._compact_css.load_from_data(
                b"button { padding: 0px 6px; min-height: 0px; }")
        btn.get_style_context().add_provider(
            TagPicker._compact_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        btn.set_can_focus(False)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_valign(Gtk.Align.CENTER)

    def _add_label_row(self, group, name, depth, ancestors):
        lbl = Gtk.Label(label=name, xalign=0)
        lbl.get_style_context().add_class("dim-label")
        lbl.set_margin_start(24 * depth)
        child = lbl
        sync_btn = None
        if self.on_add_tag or self.on_apply:
            child = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            child.pack_start(lbl, True, True, 0)
        if self.on_apply:
            sync_btn = Gtk.Button(label="→⚡")
            self._compact(sync_btn)
            sync_btn.set_no_show_all(True)  # shown only while a series is linked
            sync_btn.set_tooltip_text(
                "sync all of this group's tag states to the clip's series")
            child.pack_end(sync_btn, False, False, 0)
        if self.on_add_tag:
            add_btn = Gtk.Button(label="+")
            self._compact(add_btn)
            add_btn.set_tooltip_text("add a tag under this label (rewrites tags.txt)")
            add_btn.connect("clicked", lambda *a: self.on_add_tag(name, depth))
            child.pack_end(add_btn, False, False, 0)
        row = self._add_row(child, "label", name, group)
        if sync_btn is not None:
            sync_btn.connect("clicked", lambda *a: self._sync_group_to_series(row))
            row.apply_btn = sync_btn  # follows tag-row →⚡ visibility
        row.set_selectable(False)  # a section header, not a tag
        row.depth = depth
        row.ancestors = [a.lower() for a in ancestors]
        return row

    def _add_tag_row(self, tag, active, depth=0, ancestors=None, group=None,
                     group_label=None):
        if group is None:  # runtime additions (e.g. series apply) get their own group
            if self._extra_group is None:
                self._extra_group = self._new_group()
            group = self._extra_group
        check = Gtk.CheckButton(label=tag)
        check.set_active(active)
        check.set_can_focus(False)  # all keys are handled at the window level
        check.set_margin_start(24 * depth)
        child = check
        apply_btn = None
        handle = None
        if group_label or self.on_apply or self.on_rename_tag or self.on_delete_tag:
            child = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            if group_label:  # only label-group members are drag-reorderable
                handle = Gtk.EventBox()
                handle_lbl = Gtk.Label(label="⠿")
                handle_lbl.get_style_context().add_class("dim-label")
                handle.add(handle_lbl)
                child.pack_start(handle, False, False, 0)
            child.pack_start(check, True, True, 0)
        if self.on_apply:
            apply_btn = Gtk.Button(label="→⚡")
            self._compact(apply_btn)
            apply_btn.set_no_show_all(True)  # shown only while a series is linked
            apply_btn.set_tooltip_text(
                "apply this tag's on/off state to the clip's series (ctrl+a = selected row)")
            apply_btn.connect("clicked",
                              lambda *a: self.on_apply(tag, check.get_active()))
            child.pack_end(apply_btn, False, False, 0)
        if self.on_delete_tag:
            del_btn = Gtk.Button(label="🗑")
            self._compact(del_btn)
            del_btn.set_tooltip_text("delete this tag everywhere (tags.txt, clips, series)")
            del_btn.connect("clicked", lambda *a: self.on_delete_tag(tag))
            child.pack_end(del_btn, False, False, 0)
        if self.on_rename_tag:
            edit_btn = Gtk.Button(label="✏")
            self._compact(edit_btn)
            edit_btn.set_tooltip_text("rename this tag everywhere (tags.txt, clips, series)")
            edit_btn.connect("clicked", lambda *a: self.on_rename_tag(tag))
            child.pack_end(edit_btn, False, False, 0)
        row = self._add_row(child, "tag", tag, group)
        row.check = check
        row.apply_btn = apply_btn
        row.depth = depth
        row.ancestors = [a.lower() for a in (ancestors or [])]
        row.group_label = group_label
        if handle is not None:
            targets = [Gtk.TargetEntry.new("CLIPTAG_ROW", Gtk.TargetFlags.SAME_APP, 0)]
            handle.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets,
                                   Gdk.DragAction.MOVE)
            handle.connect("drag-begin",
                           lambda *a: setattr(self, "_drag_row", row))
            # payload must match the requested custom target — set_text would
            # answer with a TEXT type and the drop silently fails
            handle.connect("drag-data-get",
                           lambda w, ctx, sel, info, time:
                           sel.set(sel.get_target(), 8, b"row"))
            row.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.MOVE)
            row.connect("drag-data-received",
                        lambda w, ctx, x, y, sel, info, time: self._on_row_drop(row))
        return row

    def _on_row_drop(self, dest):
        src, self._drag_row = self._drag_row, None
        if (src is None or src is dest
                or src.get_parent() is not dest.get_parent()):
            return  # drops only reorder within the same label group
        self._reorder_rows(src, dest)

    def _reorder_rows(self, src, dest):
        group = src.get_parent()
        di = group.get_children().index(dest)
        group.remove(src)
        group.insert(src, di)  # lands after dest dragging down, before it up
        self._rows = [r for g in self._groups for r in g.get_children()]
        if self.on_reorder and src.group_label:
            ordered = [r.tag for r in group.get_children() if r.kind == "tag"]
            self.on_reorder(src.group_label[0], src.group_label[1], ordered)

    def _sync_group_to_series(self, label_row):
        """Push the on/off state of every tag in this label's group into
        the linked series (the group ListBox holds exactly its members)."""
        for r in label_row.get_parent().get_children():
            if r.kind == "tag":
                self.on_apply(r.tag, r.check.get_active())

    def _matches(self, row):
        if not self.query:
            return True
        if row.kind == "series":
            return False  # queries filter tags; the series section hides
        # a match pulls in its whole subtree and its ancestors for context
        return any(self.query in name for name in
                   [row.tag.lower()] + row.ancestors + row.descendants)

    def rows(self):
        return list(self._rows)

    def select_tag(self, tag):
        row = next((r for r in self._rows
                    if r.kind == "tag" and r.tag == tag), None)
        if row is not None:
            self._select(row)

    def _visible_rows(self):
        return [r for r in self._rows if self._matches(r)]

    def _selectable_rows(self):
        return [r for r in self._visible_rows() if r.kind != "label"]

    def _select(self, row):
        self._do_select(row)
        if row is None:
            return
        # a capped (scrollable) group scrolls internally first
        container = row.get_parent().container
        if isinstance(container, Gtk.ScrolledWindow):
            alloc = row.get_allocation()
            adj = container.get_vadjustment()
            if alloc.y < adj.get_value():
                adj.set_value(alloc.y)
            elif alloc.y + alloc.height > adj.get_value() + adj.get_page_size():
                adj.set_value(alloc.y + alloc.height - adj.get_page_size())
        # keep the selected row scrolled into view (columns scroll sideways)
        coords = row.translate_coordinates(self.columns_box, 0, 0)
        if not coords:
            return
        alloc = row.get_allocation()
        for adj, pos, size in (
                (self.scroller.get_vadjustment(), coords[1], alloc.height),
                (self.scroller.get_hadjustment(), coords[0], alloc.width)):
            if pos < adj.get_value():
                adj.set_value(pos)
            elif pos + size > adj.get_value() + adj.get_page_size():
                adj.set_value(pos + size - adj.get_page_size())

    def set_query(self, text):
        self.query = text
        self.query_lbl.set_text(("filter: " + text) if text else "")
        self.clear_btn.set_visible(bool(text))
        for group in self._groups:
            group.invalidate_filter()
            # hide groups with nothing visible so they free their column slot
            group.container.set_visible(
                any(self._matches(r) for r in group.get_children()))
        self._relayout()
        # nothing selected by default — ↓ enters the list at the top
        self._select(None)

    def move(self, delta):
        rows = self._selectable_rows()
        if not rows:
            return
        sel = self.selected_row()
        if sel not in rows:  # first arrow press enters the list at the top
            self._select(rows[0])
            return
        i = rows.index(sel)
        self._select(rows[max(0, min(len(rows) - 1, i + delta))])

    def toggle(self):
        row = self.selected_row()
        # labels can still be mouse-selected (FlowBoxChild can't opt out)
        if not row or row.kind == "label" or not self._matches(row):
            return
        if row.kind == "series":
            self._toggle_series(row)
        else:
            row.check.set_active(not row.check.get_active())
        self.set_query("")  # reset filter for the next tag
        self._select(row)  # ...but stay on the toggled row

    def _toggle_series(self, row):
        """Toggle the series on the clip: link + apply its tags, or — when
        it is the currently linked series — delink + untoggle its tags."""
        if row.tag == (self.applied_series or self.linked_series):
            for r in self._rows:
                if r.kind == "tag" and r.tag in row.series_tags:
                    r.check.set_active(False)
            self.applied_series = self.linked_series = None
        else:
            self.check_tags(row.series_tags)
            self.applied_series = row.tag
        self._refresh_series_labels()
        if self.on_link_changed:
            self.on_link_changed()

    def _refresh_series_labels(self):
        for r in self._rows:
            if r.kind == "series":
                r.lbl.set_text(self._series_label(r.tag))
                r.toggle_btn.set_label(self._series_btn_label(r.tag))

    def apply_new_series(self, title, tags):
        """Add (or find) a ⚡ row for a just-created series and mark it applied."""
        if not any(r.kind == "series" and r.tag == title for r in self._rows):
            if self._series_group is None:
                self._series_group = self._new_group(scroll_max=self.SERIES_MAX_HEIGHT)
                # keep the series group pinned first (top of the first column)
                self._groups.remove(self._series_group)
                self._groups.insert(0, self._series_group)
                self._series_group.container.set_visible(True)
            n_series = sum(1 for r in self._rows if r.kind == "series")
            self._add_series_row(title, tags, rows_index=n_series)
            self._relayout()
        self.applied_series = title
        self._refresh_series_labels()

    def set_apply_buttons_visible(self, visible):
        for r in self._rows:
            if getattr(r, "apply_btn", None):
                r.apply_btn.set_visible(visible)

    def update_series_tags(self, title, tags):
        for r in self._rows:
            if r.kind == "series" and r.tag == title:
                r.series_tags = list(tags)

    def check_tags(self, tags):
        have = {r.tag: r for r in self._rows if r.kind == "tag"}
        added = False
        for tag in tags:
            if tag in have:
                have[tag].check.set_active(True)
            else:
                self._add_tag_row(tag, True)
                added = True
        if added:
            self._extra_group.container.set_visible(True)
            self._relayout()

    def clear_visible(self):
        """Untoggle all visible tags — with a filter active, only the matches.
        Also de-couples the clip's series link (dropped on save)."""
        for row in self._visible_rows():
            if row.kind == "tag":
                row.check.set_active(False)
        if self.applied_series or self.linked_series:
            self.applied_series = self.linked_series = None
            self._refresh_series_labels()
            if self.on_link_changed:
                self.on_link_changed()

    def checked_tags(self):
        return [r.tag for r in self._rows
                if r.kind == "tag" and r.check.get_active()]

    def handle_key(self, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and event.keyval in (Gdk.KEY_u, Gdk.KEY_U):
            self.clear_visible()
        elif ctrl:
            return False
        elif event.keyval == Gdk.KEY_space:
            self.toggle()
        elif event.keyval == Gdk.KEY_BackSpace:
            # tap = clear query; hold >0.6s (auto-repeat events) = untoggle visible
            t = event.time
            if self._bs_last is None or t - self._bs_last > 200:
                self._bs_start = t  # new tap, not a continued hold
                self.set_query("")
            elif t - self._bs_start > 600:
                self.clear_visible()
                self._bs_start = t  # don't re-fire on every further repeat
            self._bs_last = t
        elif event.keyval == Gdk.KEY_Down:
            self.move(1)
        elif event.keyval == Gdk.KEY_Up:
            self.move(-1)
        else:
            ch = Gdk.keyval_to_unicode(event.keyval)
            if ch > 32:  # printable, background query — no input field
                self.set_query(self.query + chr(ch).lower())
                return True
            return False
        return True


def make_window(title, hint_text):
    win = Gtk.Window(title=title)
    display = Gdk.Display.get_default()
    monitor = display.get_primary_monitor() or display.get_monitor(0)
    geo = monitor.get_geometry()
    # wide enough for the flow columns, tall enough to avoid wrapping early
    win.set_default_size(int(geo.width * 0.5), int(geo.height * 0.95))
    Gtk.Widget.set_opacity(win, 0.8)  # keep the video visible behind the dialog
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.set_border_width(10)
    win.add(box)
    hint = Gtk.Label(label=hint_text)
    hint.get_style_context().add_class("dim-label")
    hint.set_line_wrap(True)
    return win, box, hint


def run_main(win):
    win.connect("destroy", lambda *a: Gtk.main_quit() if Gtk.main_level() else None)
    win.show_all()
    if os.environ.get("CLIPTAG_AUTOCLOSE"):
        GLib.timeout_add(600, Gtk.main_quit)
    Gtk.main()
    win.destroy()


def tags_dialog(root, db_path, clip):
    rel = os.path.relpath(clip, root)
    db = load_db(db_path)
    entry = db.setdefault("clips", {}).setdefault(rel, {})
    current = set(entry.get("tags", []))
    options = load_options(root)
    # keep db-only tags visible so a save can't silently drop them
    known = {tag for tag, depth in options}
    options += [(tag, 0) for tag in sorted(current.difference(known))]

    win, box, hint = make_window("Clip Tags", HINT_PICKER + "\n⚡ rows are series: space applies their tags + links the clip (✓)")
    name_lbl = Gtk.Label(label=os.path.basename(clip))
    name_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
    def apply_tag_to_series(tag, active):
        title = picker.applied_series or picker.linked_series
        if not title or title not in db.get("series", {}):
            return
        stags = db["series"][title].setdefault("tags", [])
        if active and tag not in stags:
            stags.append(tag)
        elif not active and tag in stags:
            stags.remove(tag)
        save_db(db_path, db)
        picker.update_series_tags(title, stags)  # keep the ⚡ row's apply fresh

    def reload_picker(checked):
        opts = load_options(root)
        known = {t for t, d in opts}
        opts += [(t, 0) for t in sorted(checked.difference(known))]
        picker.reload(opts, checked, db.get("series", {}))
        sync_apply_buttons()

    def add_tag_under_label(label, depth):
        name = prompt_text(win, 'Add tag under "%s"' % label)
        if name and add_tag_to_label(root, label, depth, name):
            reload_picker(set(picker.checked_tags()))
            picker.select_tag(name)  # ready to toggle with space right away

    def rename_tag(tag):
        new = prompt_text(win, 'Rename tag "%s"' % tag, tag)
        if not new or new == tag:
            return
        rename_tag_everywhere(root, db, tag, new)
        save_db(db_path, db)
        reload_picker({new if t == tag else t for t in picker.checked_tags()})

    def delete_tag(tag):
        if not confirm_text(win, 'Delete tag "%s" everywhere?' % tag):
            return
        delete_tag_everywhere(root, db, tag)
        save_db(db_path, db)
        reload_picker(set(picker.checked_tags()) - {tag})

    picker = TagPicker(options, current, db.get("series", {}), entry.get("series"),
                       on_apply=apply_tag_to_series, on_add_tag=add_tag_under_label,
                       on_rename_tag=rename_tag, on_delete_tag=delete_tag)

    def sync_apply_buttons():
        picker.set_apply_buttons_visible(
            bool(picker.applied_series or picker.linked_series))

    picker.on_link_changed = sync_apply_buttons  # covers mouse button path too
    picker.on_reorder = lambda label, depth, ordered: \
        reorder_label_group(root, label, depth, ordered)

    create_btn = Gtk.Button(label="Create series")
    create_btn.set_can_focus(False)
    create_btn.set_tooltip_text("new series from this clip's checked tags, and link the clip to it (ctrl+s)")
    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    actions.pack_end(create_btn, False, False, 0)
    notes_lbl = Gtk.Label(label="notes (tab = enter/leave)", xalign=0)
    notes_lbl.get_style_context().add_class("dim-label")
    notes_view = Gtk.TextView()
    notes_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    notes_view.get_buffer().set_text(entry.get("notes", ""))
    notes_frame = Gtk.Frame()
    notes_scroller = Gtk.ScrolledWindow()
    notes_scroller.set_size_request(-1, 70)
    notes_scroller.add(notes_view)
    notes_frame.add(notes_scroller)
    box.pack_start(name_lbl, False, False, 0)
    box.pack_start(picker.widget, True, True, 0)
    box.pack_start(actions, False, False, 0)
    box.pack_start(notes_lbl, False, False, 0)
    box.pack_start(notes_frame, False, False, 0)
    box.pack_start(hint, False, False, 0)

    result = {"tags": None, "notes": ""}

    def create_series(*a):
        title = prompt_text(win, "Create series",
                            os.path.splitext(os.path.basename(clip))[0])
        if not title:
            return
        # existing title: just link the clip to it, don't clobber its tags
        if title not in db.setdefault("series", {}):
            db["series"][title] = {"tags": picker.checked_tags()}
        entry["series"] = title  # overwrites a previously assigned series
        save_db(db_path, db)
        picker.apply_new_series(title, db["series"][title]["tags"])
        sync_apply_buttons()

    create_btn.connect("clicked", create_series)

    def on_key(widget, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        elif notes_view.has_focus():
            # typing belongs to the notes textarea; tab returns to the list
            if event.keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
                win.set_focus(None)
                return True
            return False
        elif event.keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            notes_view.grab_focus()
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            result["tags"] = picker.checked_tags()
            buf = notes_view.get_buffer()
            result["notes"] = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            Gtk.main_quit()
        elif ctrl and event.keyval in (Gdk.KEY_s, Gdk.KEY_S):
            create_series()
        elif ctrl and event.keyval in (Gdk.KEY_a, Gdk.KEY_A):
            row = picker.selected_row()
            if row and row.kind == "tag":
                apply_tag_to_series(row.tag, row.check.get_active())
        else:
            handled = picker.handle_key(event)
            sync_apply_buttons()  # applying a series row links the clip
            return handled
        return True

    win.connect("key-press-event", on_key)
    sync_apply_buttons()
    run_main(win)

    if result["tags"] is None:
        print("CANCELLED")
        return
    entry["tags"] = result["tags"]
    notes = result["notes"].strip()
    if notes:
        entry["notes"] = notes
    else:
        entry.pop("notes", None)
    link = picker.applied_series or picker.linked_series
    if link:
        entry["series"] = link
    else:
        entry.pop("series", None)  # cleared-all dialogs de-couple the series
    save_db(db_path, db)
    print("SAVED: " + (", ".join(result["tags"]) if result["tags"] else "(none)"))


def series_dialog(root, db_path):
    db = load_db(db_path)
    series = db.setdefault("series", {})
    base_options = load_options(root)
    state = {"title": None, "picker": None, "suppress": False}

    win, box, hint = make_window("Clip Series", HINT_SERIES)
    combo = Gtk.ComboBoxText()
    combo.set_can_focus(False)
    buttons = {}
    top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    top.pack_start(combo, True, True, 0)
    for label in ("New", "Rename", "Delete"):
        b = buttons[label] = Gtk.Button(label=label)
        b.set_can_focus(False)
        top.pack_start(b, False, False, 0)
    placeholder = Gtk.Label(label="select a series (←→ or dropdown) · ctrl+n (or New) to create one")
    placeholder.set_no_show_all(True)  # visibility managed by load_series
    picker_slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.pack_start(top, False, False, 0)
    box.pack_start(placeholder, False, False, 6)
    box.pack_start(picker_slot, True, True, 0)
    box.pack_start(hint, False, False, 0)

    def prompt(title_text, default=""):
        return prompt_text(win, title_text, default)

    def confirm(text):
        dlg = Gtk.MessageDialog(transient_for=win, modal=True,
                                message_type=Gtk.MessageType.QUESTION,
                                buttons=Gtk.ButtonsType.YES_NO, text=text)
        resp = dlg.run()
        dlg.destroy()
        return resp == Gtk.ResponseType.YES

    def save_current():
        if state["title"] is not None and state["picker"] is not None:
            series[state["title"]]["tags"] = state["picker"].checked_tags()
            save_db(db_path, db)

    def load_series(title):
        save_current()
        state["title"] = title
        if title is None:
            if state["picker"]:
                state["picker"].widget.hide()
            placeholder.show()
            return
        stags = series[title].get("tags", [])
        known = {tag for tag, depth in base_options}
        options = base_options + [(t, 0) for t in sorted(set(stags).difference(known))]
        if state["picker"] is None:
            state["picker"] = TagPicker(options, set(stags),
                                        on_add_tag=add_tag_under_label,
                                        on_rename_tag=rename_tag,
                                        on_delete_tag=delete_tag)
            state["picker"].on_reorder = lambda label, depth, ordered: \
                reorder_label_group(root, label, depth, ordered)
            picker_slot.pack_start(state["picker"].widget, True, True, 0)
        else:
            state["picker"].reload(options, set(stags))
        placeholder.hide()
        state["picker"].widget.show_all()

    def reload_picker(checked):
        base_options[:] = load_options(root)
        picker = state["picker"]
        if picker is not None and state["title"] is not None:
            known = {t for t, d in base_options}
            opts = base_options + [(t, 0) for t in sorted(checked.difference(known))]
            picker.reload(opts, checked)

    def add_tag_under_label(label, depth):
        name = prompt('Add tag under "%s"' % label)
        if name and add_tag_to_label(root, label, depth, name):
            reload_picker(set(state["picker"].checked_tags()))
            state["picker"].select_tag(name)  # ready to toggle with space

    def rename_tag(tag):
        new = prompt('Rename tag "%s"' % tag, tag)
        if not new or new == tag:
            return
        rename_tag_everywhere(root, db, tag, new)
        save_db(db_path, db)
        reload_picker({new if t == tag else t
                       for t in state["picker"].checked_tags()})

    def delete_tag(tag):
        if not confirm('Delete tag "%s" everywhere?' % tag):
            return
        delete_tag_everywhere(root, db, tag)
        save_db(db_path, db)
        reload_picker(set(state["picker"].checked_tags()) - {tag})

    def refresh_combo(select_title):
        state["suppress"] = True
        combo.remove_all()
        titles = sorted(series)
        for t in titles:
            combo.append_text(t)
        if select_title in titles:
            combo.set_active(titles.index(select_title))
        state["suppress"] = False

    def on_combo_changed(c):
        if not state["suppress"] and c.get_active_text():
            load_series(c.get_active_text())

    combo.connect("changed", on_combo_changed)

    def new_series(*a):
        title = prompt("New series")
        if not title or title in series:
            return
        save_current()
        series[title] = {"tags": []}
        save_db(db_path, db)
        refresh_combo(title)
        load_series(title)

    def rename_series(*a):
        old = state["title"]
        if old is None:
            return
        title = prompt("Rename series", old)
        if not title or title == old or title in series:
            return
        save_current()
        series[title] = series.pop(old)
        relink_series(db, old, title)
        state["title"] = title
        save_db(db_path, db)
        refresh_combo(title)

    def delete_series(*a):
        title = state["title"]
        if title is None or not confirm('Delete series "%s"?' % title):
            return
        series.pop(title)
        relink_series(db, title, None)
        save_db(db_path, db)
        state["title"] = None  # already gone — don't save it again
        remaining = sorted(series)
        nxt = remaining[0] if remaining else None
        refresh_combo(nxt)
        load_series(nxt)

    buttons["New"].connect("clicked", new_series)
    buttons["Rename"].connect("clicked", rename_series)
    buttons["Delete"].connect("clicked", delete_series)

    def cycle(delta):
        titles = sorted(series)
        if not titles:
            return
        i = titles.index(state["title"]) if state["title"] in titles else 0
        combo.set_active((i + delta) % len(titles))  # triggers load via changed

    def on_key(widget, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            save_current()
            Gtk.main_quit()
        elif ctrl and event.keyval in (Gdk.KEY_n, Gdk.KEY_N):
            new_series()
        elif ctrl and event.keyval in (Gdk.KEY_r, Gdk.KEY_R):
            rename_series()
        elif ctrl and event.keyval in (Gdk.KEY_d, Gdk.KEY_D):
            delete_series()
        elif event.keyval == Gdk.KEY_Left:
            cycle(-1)
        elif event.keyval == Gdk.KEY_Right:
            cycle(1)
        elif state["picker"] and state["picker"].widget.get_visible():
            return state["picker"].handle_key(event)
        else:
            return False
        return True

    win.connect("key-press-event", on_key)
    refresh_combo(None)  # open blank — no series preselected
    load_series(None)
    run_main(win)
    print("DONE")


def main():
    mode = sys.argv[1]
    clip = sys.argv[2] if len(sys.argv) > 2 else None
    resolved = resolve_root(clip)
    if resolved is None:
        print("NODB")
        return
    root, db_path = resolved
    if mode == "tags":
        tags_dialog(root, db_path, clip)
    elif mode == "series":
        series_dialog(root, db_path)
    else:
        sys.exit("unknown mode: " + mode)


if __name__ == "__main__":
    main()
