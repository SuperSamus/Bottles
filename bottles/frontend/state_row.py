# state_row.py
#
# Copyright 2025 The Bottles Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from datetime import datetime
from gettext import gettext as _

from gi.repository import Gtk, Adw

from bottles.backend.utils.threading import RunAsync
from bottles.frontend.gtk import GtkUtils


@Gtk.Template(resource_path="/com/usebottles/bottles/state-row.ui")
class StateRow(Adw.ActionRow):
    __gtype_name__ = "StateRow"

    # region Widgets
    btn_restore = Gtk.Template.Child()
    spinner = Gtk.Template.Child()

    # endregion

    def __init__(self, parent, config, state, active, **kwargs):
        super().__init__(**kwargs)

        # common variables and references
        self.parent = parent
        self.window = parent.window
        self.manager = parent.window.manager
        self.queue = parent.window.page_details.queue
        self.state = state

        if config.Versioning:
            self.state_name = "#{} - {}".format(
                state[0],
                datetime.strptime(
                    state[1]["Creation_Date"], "%Y-%m-%d %H:%M:%S.%f"
                ).strftime("%d %B %Y, %H:%M"),
            )

            self.set_subtitle(self.state[1]["Comment"])
            if state[0] == config.State:
                self.add_css_class("current-state")
        else:
            self.state_name = "{} - {}".format(
                state[0],
                datetime.fromtimestamp(state[1]["timestamp"]).strftime(
                    "%d %B %Y, %H:%M"
                ),
            )
            self.set_subtitle(state[1]["message"])
            if active:
                self.add_css_class("current-state")

        self.set_title(self.state_name)
        self.config = config
        self.versioning_manager = self.manager.versioning_manager

        # connect signals
        self.btn_restore.connect("clicked", self.set_state)

    def set_state(self, widget):
        """
        Set the bottle state to this one.
        """

        def handle_response(dialog, response_id):
            if response_id == "ok":
                self.queue.add_task()
                self.parent.set_sensitive(False)
                self.spinner.show()
                self.spinner.start()

                def _after():
                    self.window.page_details.view_versioning.update(None, self.config)
                    self.manager.update_bottles()

                RunAsync(
                    task_func=self.versioning_manager.set_state,
                    callback=self.set_completed,
                    config=self.config,
                    state_id=self.state[0],
                    after=_after,
                )
            dialog.destroy()

        dialog = Adw.MessageDialog.new(
            self.window,
            _("Are you sure you want to restore this state?"),
            _(
                "Restoring this state will overwrite the current configuration and cannot be undone."
            ),
        )
        dialog.add_response("cancel", _("_Cancel"))
        dialog.add_response("ok", _("_Restore"))
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", handle_response)
        dialog.present()

    @GtkUtils.run_in_main_loop
    def set_completed(self, result, error=False):
        """
        Set completed status to the widget.
        """
        if not self.config.Versioning and result.message:
            self.window.show_toast(result.message)
        self.spinner.stop()
        self.spinner.hide()
        self.btn_restore.set_visible(False)
        self.parent.set_sensitive(True)
        self.queue.end_task()
        self.manager.update_bottles()
        config = self.manager.local_bottles[self.config.Path]
        self.window.page_details.set_config(config)
