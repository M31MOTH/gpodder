# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2016 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
import os


import gpodder

_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder.gtkui.draw import draw_text_box_centered


class gPodderShownotes:
    def __init__(self, shownotes_pane):
        self.shownotes_pane = shownotes_pane

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.init())
        self.scrolled_window.show_all()

        self.da_message = Gtk.DrawingArea()
        self.da_message.set_property('expand', True)
        self.da_message.connect('draw', self.on_shownotes_message_expose_event)
        self.shownotes_pane.add(self.da_message)
        self.shownotes_pane.add(self.scrolled_window)

        self.set_complain_about_selection(True)
        self.hide_pane()

    # Either show the shownotes *or* a message, 'Please select an episode'
    def set_complain_about_selection(self, message=True):
        if message:
            self.scrolled_window.hide()
            self.da_message.show()
        else:
            self.da_message.hide()
            self.scrolled_window.show()

    def set_episodes(self, selected_episodes):
        if self.pane_is_visible:
            if len(selected_episodes) == 1:
                episode = selected_episodes[0]
                heading = episode.title
                subheading = _('from %s') % (episode.channel.title)
                self.update(heading, subheading, episode)
                self.set_complain_about_selection(False)
            else:
                self.set_complain_about_selection(True)

    def show_pane(self, selected_episodes):
        self.pane_is_visible = True
        self.set_episodes(selected_episodes)
        self.shownotes_pane.show()

    def hide_pane(self):
        self.pane_is_visible = False
        self.shownotes_pane.hide()

    def toggle_pane_visibility(self, selected_episodes):
        if self.pane_is_visible:
            self.hide_pane()
        else:
            self.show_pane(selected_episodes)

    def on_shownotes_message_expose_event(self, drawingarea, ctx):
        # paint the background white
        ctx.set_source_rgba(1,1,1)
        x1, y1, x2, y2 = ctx.clip_extents()
        ctx.rectangle(x1, y1, x2 - x1, y2 - y1)
        ctx.fill()

        width, height = drawingarea.get_allocated_width(), drawingarea.get_allocated_height(),
        text = _('Please select an episode')
        draw_text_box_centered(ctx, drawingarea, width, height, text, None, None)
        return False


class gPodderShownotesText(gPodderShownotes):
    def init(self):
        self.text_view = Gtk.TextView()
        self.text_view.set_property('expand', True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_border_width(10)
        self.text_view.set_editable(False)
        self.text_view.connect('button-release-event', self.on_button_release)
        self.text_view.connect('key-press-event', self.on_key_press)
        self.text_buffer = Gtk.TextBuffer()
        self.text_buffer.create_tag('heading', scale=2, weight=Pango.Weight.BOLD)
        self.text_buffer.create_tag('subheading', scale=1.5)
        self.text_buffer.create_tag('hyperlink', foreground="#0000FF", underline=Pango.Underline.SINGLE)
        self.text_view.set_buffer(self.text_buffer)
        return self.text_view

    def update(self, heading, subheading, episode):
        hyperlinks = [(0, None)]
        self.text_buffer.set_text('')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), heading, 'heading')
        self.text_buffer.insert_at_cursor('\n')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), subheading, 'subheading')
        self.text_buffer.insert_at_cursor('\n\n')
        for target, text in util.extract_hyperlinked_text(episode.description):
            hyperlinks.append((self.text_buffer.get_char_count(), target))
            if target:
                self.text_buffer.insert_with_tags_by_name(
                    self.text_buffer.get_end_iter(), text, 'hyperlink')
            else:
                self.text_buffer.insert(
                    self.text_buffer.get_end_iter(), text)
        hyperlinks.append((self.text_buffer.get_char_count(), None))
        self.hyperlinks = [(start, end, url) for (start, url), (end, _) in zip(hyperlinks, hyperlinks[1:]) if url]
        self.text_buffer.place_cursor(self.text_buffer.get_start_iter())

    def on_button_release(self, widget, event):
        if event.button == 1:
            self.activate_links()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            self.activate_links()
            return True

        return False

    def activate_links(self):
        if self.text_buffer.get_selection_bounds() == ():
            pos = self.text_buffer.props.cursor_position
            target = next((url for start, end, url in self.hyperlinks if start < pos < end), None)
            if target is not None:
                util.open_website(target)
