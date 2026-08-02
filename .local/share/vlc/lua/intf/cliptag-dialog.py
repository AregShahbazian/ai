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
             Series show as pinned "⚡ title" rows — space on one
             toggles-on all its tags (one-time template apply).
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
                          { "tags": [...], "series": "<title>" } },
            "series": { "<title>": { "tags": [...] } } }
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
    """Return [(tag, depth), ...] from <root>/tags.txt; leading tabs nest a
    tag under the previous less-indented one."""
    try:
        with open(os.path.join(root, "tags.txt")) as f:
            return [(ln.strip(), len(ln) - len(ln.lstrip("\t")))
                    for ln in f if ln.strip()]
    except FileNotFoundError:
        return []


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

    def __init__(self, tags, checked, series=None, linked_series=None):
        self.query = ""
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

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_filter_func(lambda row, *a: self._matches(row))
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_vexpand(True)
        self.scroller.add(self.listbox)

        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.widget.pack_start(bar, False, False, 0)
        self.widget.pack_start(self.scroller, True, True, 0)
        self.reload(tags, checked, series)

    def reload(self, tags, checked, series=None):
        for row in self.listbox.get_children():
            row.destroy()
        for title in sorted(series or {}):
            self._add_series_row(title, series[title].get("tags", []))
        stack = []  # ancestor chain while walking the indented list
        for item in tags:
            tag, depth = item if isinstance(item, tuple) else (item, 0)
            depth = min(depth, len(stack))  # tolerate indent jumps
            stack = stack[:depth]
            if tag.startswith("#"):
                tag = tag.lstrip("#").strip()
                self._add_label_row(tag, depth, list(stack))
            else:
                self._add_tag_row(tag, tag in checked, depth, list(stack))
            stack.append(tag)
        # each row's descendant names, so filtering can keep subtrees together.
        # A label's group also spans following SAME-depth rows (a section
        # header), until the next label there or a shallower line.
        rows = [r for r in self.listbox.get_children() if r.kind != "series"]
        for i, row in enumerate(rows):
            for below in rows[i + 1:]:
                if row.kind == "label":
                    if below.depth < row.depth or (
                            below.kind == "label" and below.depth <= row.depth):
                        break
                    below.ancestors.append(row.tag.lower())
                elif below.depth <= row.depth:
                    break
                row.descendants.append(below.tag.lower())
        self.set_query("")

    def _add_row(self, child, kind, tag):
        row = Gtk.ListBoxRow()
        row.add(child)
        row.set_can_focus(False)
        row.kind, row.tag = kind, tag
        row.depth, row.ancestors, row.descendants = 0, [], []
        self.listbox.add(row)
        row.show_all()
        return row

    def _series_label(self, title):
        linked = self.applied_series or self.linked_series
        return "⚡ " + title + (" ✓" if title == linked else "")

    def _add_series_row(self, title, tags):
        lbl = Gtk.Label(label=self._series_label(title), xalign=0)
        lbl.get_style_context().add_class("dim-label")
        row = self._add_row(lbl, "series", title)
        row.series_tags = list(tags)
        row.lbl = lbl
        return row

    def _add_label_row(self, name, depth, ancestors):
        lbl = Gtk.Label(label=name, xalign=0)
        lbl.get_style_context().add_class("dim-label")
        lbl.set_margin_start(24 * depth)
        row = self._add_row(lbl, "label", name)
        row.set_selectable(False)  # a section header, not a tag
        row.depth = depth
        row.ancestors = [a.lower() for a in ancestors]

    def _add_tag_row(self, tag, active, depth=0, ancestors=None):
        check = Gtk.CheckButton(label=tag)
        check.set_active(active)
        check.set_can_focus(False)  # all keys are handled at the window level
        check.set_margin_start(24 * depth)
        row = self._add_row(check, "tag", tag)
        row.check = check
        row.depth = depth
        row.ancestors = [a.lower() for a in (ancestors or [])]

    def _matches(self, row):
        if not self.query:
            return True
        # a match pulls in its whole subtree and its ancestors for context
        return any(self.query in name for name in
                   [row.tag.lower()] + row.ancestors + row.descendants)

    def _visible_rows(self):
        return [r for r in self.listbox.get_children() if self._matches(r)]

    def _selectable_rows(self):
        return [r for r in self._visible_rows() if r.kind != "label"]

    def _select(self, row):
        self.listbox.select_row(row)
        if row is None:
            return
        # keep the selected row scrolled into view
        alloc = row.get_allocation()
        adj = self.scroller.get_vadjustment()
        if alloc.y < adj.get_value():
            adj.set_value(alloc.y)
        elif alloc.y + alloc.height > adj.get_value() + adj.get_page_size():
            adj.set_value(alloc.y + alloc.height - adj.get_page_size())

    def set_query(self, text):
        self.query = text
        self.query_lbl.set_text(("filter: " + text) if text else "")
        self.clear_btn.set_visible(bool(text))
        self.listbox.invalidate_filter()
        rows = self._selectable_rows()
        self._select(rows[0] if rows else None)

    def move(self, delta):
        rows = self._selectable_rows()
        if not rows:
            return
        sel = self.listbox.get_selected_row()
        i = rows.index(sel) if sel in rows else 0
        self._select(rows[max(0, min(len(rows) - 1, i + delta))])

    def toggle(self):
        row = self.listbox.get_selected_row()
        if not row or not self._matches(row):
            return
        if row.kind == "series":
            self.check_tags(row.series_tags)
            self.applied_series = row.tag
            self._refresh_series_labels()
        else:
            row.check.set_active(not row.check.get_active())
        self.set_query("")  # reset filter for the next tag
        self._select(row)  # ...but stay on the toggled row

    def _refresh_series_labels(self):
        for r in self.listbox.get_children():
            if r.kind == "series":
                r.lbl.set_text(self._series_label(r.tag))

    def apply_new_series(self, title, tags):
        """Add (or find) a ⚡ row for a just-created series and mark it applied."""
        rows = self.listbox.get_children()
        if not any(r.kind == "series" and r.tag == title for r in rows):
            row = self._add_series_row(title, tags)
            # keep series rows pinned at the top, above the tag rows
            n_series = sum(1 for r in rows if r.kind == "series")
            self.listbox.remove(row)
            self.listbox.insert(row, n_series)
        self.applied_series = title
        self._refresh_series_labels()

    def check_tags(self, tags):
        have = {r.tag: r for r in self.listbox.get_children() if r.kind == "tag"}
        for tag in tags:
            if tag in have:
                have[tag].check.set_active(True)
            else:
                self._add_tag_row(tag, True)

    def clear_visible(self):
        """Untoggle all visible tags — with a filter active, only the matches."""
        for row in self._visible_rows():
            if row.kind == "tag":
                row.check.set_active(False)

    def checked_tags(self):
        return [r.tag for r in self.listbox.get_children()
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
    win.set_default_size(420, int(monitor.get_geometry().height * 0.95))
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
    picker = TagPicker(options, current, db.get("series", {}), entry.get("series"))
    create_btn = Gtk.Button(label="Create series")
    create_btn.set_can_focus(False)
    create_btn.set_tooltip_text("new series from this clip's checked tags, and link the clip to it (ctrl+s)")
    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    actions.pack_end(create_btn, False, False, 0)
    box.pack_start(name_lbl, False, False, 0)
    box.pack_start(picker.widget, True, True, 0)
    box.pack_start(actions, False, False, 0)
    box.pack_start(hint, False, False, 0)

    result = {"tags": None}

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

    create_btn.connect("clicked", create_series)

    def on_key(widget, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            result["tags"] = picker.checked_tags()
            Gtk.main_quit()
        elif ctrl and event.keyval in (Gdk.KEY_s, Gdk.KEY_S):
            create_series()
        else:
            return picker.handle_key(event)
        return True

    win.connect("key-press-event", on_key)
    run_main(win)

    if result["tags"] is None:
        print("CANCELLED")
        return
    entry["tags"] = result["tags"]
    if picker.applied_series:
        entry["series"] = picker.applied_series
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
    placeholder = Gtk.Label(label="no series yet — ctrl+n (or New) to create one")
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
            state["picker"] = TagPicker(options, set(stags))
            picker_slot.pack_start(state["picker"].widget, True, True, 0)
        else:
            state["picker"].reload(options, set(stags))
        placeholder.hide()
        state["picker"].widget.show_all()

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
    refresh_combo(sorted(series)[0] if series else None)
    load_series(sorted(series)[0] if series else None)
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
