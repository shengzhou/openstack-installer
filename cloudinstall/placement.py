# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import defaultdict
import logging

import pprint

from urwid import (Button, Columns, Filler, GridFlow,
                   Padding, Pile, Text, WidgetWrap)

from cloudinstall.utils import load_charms

log = logging.getLogger('cloudinstall.placement')

BUTTON_SIZE = 12


class PlaceholderMachine:
    """A dummy machine that doesn't map to an existing maas machine"""

    def __init__(self, instance_id, name):
        self.instance_id = instance_id
        self.name = name        # TODO name or display_name or what?

    @property
    def hostname(self):
        return self.name

    def __repr__(self):
        return "<Placeholder Machine: {}>".format(self.name)


class PlacementController:
    """Keeps state of current machines and their assigned services.
    """

    def __init__(self, maas_state):
        self.maas_state = maas_state
        self.assignments = defaultdict(list)  # instance_id -> [charm class]
        self.first_available = PlaceholderMachine("first-available",
                                                  "First Available")

    def machines(self):
        return [self.first_available] + self.maas_state.machines()

    def charm_classes(self):
        return [m.__charm_class__ for m in load_charms()
                if not m.__charm_class__.disabled]

    def assign(self, instance_id, charm_class):
        for m, l in self.assignments.items():
            if charm_class in l:
                l.remove(charm_class)
        self.assignments[instance_id] = charm_class

    def machine_for_charm(self, charm_class):
        machines = self.machines()
        for m_id, l in self.assignments.items():
            if charm_class in l:
                return next((m for m in machines
                             if m.instance_id == m_id), None)
        return None

    def remove_assignment(self, m, cc):
        assignments = self.assignments[m.instance_id]
        assignments.remove(cc)

    def clear_assignments(self, m):
        del self.assignments[m.instance_id]

    def assignments_for_machine(self, m):
        return self.assignments[m.instance_id]

    def set_all_assignments(self, assignments):
        self.assignments = assignments

    def gen_defaults(self):
        assignments = defaultdict(list)

        maas_machines = self.maas_state.machines()

        def machine_or_first_avail(index):
            if len(maas_machines) > index:
                return maas_machines[index]
            else:
                return self.first_available

        cur_machine = 0
        m_controller = machine_or_first_avail(cur_machine)
        cur_machine += 1

        for charm_class in self.charm_classes():

            if charm_class.isolate:
                machine = machine_or_first_avail(cur_machine)
                cur_machine += 1
                assignments[machine.instance_id].append(charm_class)
            else:
                assignments[m_controller.instance_id].append(charm_class)

        log.debug("Assignments generated: " + pprint.pformat(assignments))
        return assignments


class MachineWidget(WidgetWrap):
    def __init__(self, machine, controller, actions):
        self.machine = machine
        self.controller = controller
        self.actions = actions
        w = self.build_widgets()
        self.update()
        super().__init__(w)

    def build_widgets(self):
        self.machine_info_widget = Text("\N{TAPE DRIVE} {}".format(
            self.machine.hostname))
        self.assignments_widget = Text("")

        buttons = []
        for label, func in self.actions:
            b = Button(label, on_press=func, user_data=self.machine)
            buttons.append(b)

        button_grid = GridFlow(buttons, BUTTON_SIZE, 1, 1, 'right')

        p = Pile([self.machine_info_widget,
                  self.assignments_widget,
                  button_grid])

        return Padding(p, left=2, right=2)

    def update(self):
        self.assignments = self.controller.assignments_for_machine(
            self.machine)

        astr = '  assignments: ' + ', '.join([c.display_name for c in
                                              self.assignments])
        self.assignments_widget.set_text(astr)


class ServiceWidget(WidgetWrap):
    def __init__(self, charm_class, controller, actions):
        self.charm_class = charm_class
        self.controller = controller
        self.actions = actions
        w = self.build_widgets()
        self.update()
        super().__init__(w)

    def selectable(self):
        return True

    def build_widgets(self):
        self.charm_info_widget = Text("\N{GEAR} {}".format(
            self.charm_class.display_name))
        self.assignment_widget = Text("")

        buttons = []
        for label, func in self.actions:
            b = Button(label, on_press=func, user_data=self.charm_class)
            buttons.append(b)

        button_grid = GridFlow(buttons, BUTTON_SIZE, 1, 1, 'right')

        p = Pile([self.charm_info_widget,
                  self.assignment_widget,
                  button_grid])
        return Padding(p, left=2, right=2)

    def update(self):
        m = self.controller.machine_for_charm(self.charm_class)
        if m is None:
            self.assignment_widget.set_text("  \N{DOTTED CIRCLE} Unassigned")
        else:
            self.assignment_widget.set_text("  \N{TAPE DRIVE} {}".format(
                m.hostname))


class MachinesList(WidgetWrap):
    """A list of machines with configurable action buttons for each
    machine.

    actions - a list of ('label', function) pairs that wil be used to
    create buttons for each machine.  The machine will be passed to
    the function as userdata.
    """

    def __init__(self, controller, actions):
        self.controller = controller
        self.actions = actions
        self.machine_widgets = []
        w = self.build_widgets()
        super().__init__(w)

    def selectable(self):
        # overridden to ensure that we can arrow through the buttons
        # shouldn't be necessary according to documented behavior of
        # Pile & Columns, but discovered via trial & error.
        return True

    def build_widgets(self):
        self.machine_pile = Pile([Text("Machines")] +
                                 self.machine_widgets)
        return self.machine_pile

    def update(self):

        def find_widget(m):
            return next((mw for mw in self.machine_widgets if
                         mw.machine.instance_id == m.instance_id), None)

        for m in self.controller.machines():
            mw = find_widget(m)
            if mw is None:
                mw = self.add_machine_widget(m)
            mw.update()

    def add_machine_widget(self, machine):
        mw = MachineWidget(machine, self.controller, self.actions)
        self.machine_widgets.append(mw)
        options = self.machine_pile.options()
        self.machine_pile.contents.append((mw, options))
        return mw


class ServicesList(WidgetWrap):
    """A list of services (charm classes) with configurable action buttons
    for each machine.

    actions - a list of ('label', function) pairs that wil be used to
    create buttons for each machine.  The machine will be passed to
    the function as userdata.
    """

    def __init__(self, controller, actions):
        self.controller = controller
        self.actions = actions
        self.service_widgets = []
        w = self.build_widgets()
        super().__init__(w)

    def selectable(self):
        # overridden to ensure that we can arrow through the buttons
        # shouldn't be necessary according to documented behavior of
        # Pile & Columns, but discovered via trial & error.
        return True

    def build_widgets(self):
        self.service_pile = Pile([Text("Services")] +
                                 self.service_widgets)
        return self.service_pile

    def update(self):

        def find_widget(cc):
            return next((sw for sw in self.service_widgets if
                         sw.charm_class.charm_name == cc.charm_name), None)

        for cc in self.controller.charm_classes():
            sw = find_widget(cc)
            if sw is None:
                sw = self.add_service_widget(cc)
            sw.update()

    def add_service_widget(self, charm_class):
        sw = ServiceWidget(charm_class, self.controller, self.actions)
        self.service_widgets.append(sw)
        options = self.service_pile.options()
        self.service_pile.contents.append((sw, options))
        return sw


class PlacementView(WidgetWrap):
    """Handles display of machines and services.

    displays nothing if self.controller is not set.
    set it to a PlacementController.
    """

    def __init__(self, controller):
        self.controller = controller
        w = self.build_widgets()
        super().__init__(w)
        self.update()

    def update(self):
        self.machines_list.update()
        self.services_list.update()

    def scroll_down(self):
        pass

    def scroll_up(self):
        pass

    def build_widgets(self):
        self.charm_store_pile = Pile([Text("Add Charms")])

        self.machines_list = MachinesList(self.controller,
                                          [('Clear', self.do_clear_machine)])
        self.machines_list.update()

        self.services_list = ServicesList(self.controller,
                                          [('Clear', self.do_clear_service)])
        self.services_list.update()

        cols = Columns([self.charm_store_pile,
                        self.services_list,
                        self.machines_list])

        return Filler(cols, valign='top')

    def do_clear_machine(self, sender, machine):
        self.controller.clear_assignments(machine)

    def do_clear_service(self, sender, charm_class):
        m = self.controller.machine_for_charm(charm_class)
        if m is not None:
            self.controller.remove_assignment(m, charm_class)
