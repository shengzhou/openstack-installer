#
# machine.py - Machine
#
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

class Machine:
    """ Base machine class """

    def __init__(self, machine_id, machine):
        self.machine_id = machine_id
        self.machine = machine
        self._cpu_cores = self.hardware('cpu-cores')
        self._storage = self.hardware('root-disk')
        self._mem = self.hardware('memory')

    @property
    def is_machine_0(self):
        """ Checks if machine is bootstrapped node

        :rtype: bool
        """
        return "0" in self.machine_id

    @property
    def is_machine_1(self):
        """ Checks if machine is first machine

        This holds the openstack services needed
        to manage your cloud. Everything except
        nova-compute should be deployed here.

        :rtype: bool
        """
        return "1" in self.machine_id

    @property
    def cpu_cores(self):
        """ Return number of cpu-cores

        :returns: number of cpus
        :rtype: str
        """
        return self._cpu_cores

    @cpu_cores.setter
    def cpu_cores(self, val):
        self._cpu_cores = val

    @property
    def arch(self):
        """ Return architecture

        :returns: architecture type
        :rtype: str
        """
        return self.hardware('arch')

    @property
    def storage(self):
        """ Return storage

        :returns: storage size
        :rtype: str
        """
        try:
            _storage_in_gb = int(self._storage[:-1]) / 1024
        except ValueError:
            return "N/A"
        return "{size}G".format(size=str(_storage_in_gb))

    @storage.setter
    def storage(self, val):
        self._storage = val

    @property
    def mem(self):
        """ Return memory

        :returns: memory size
        :rtype: str
        """
        try:
            _mem = int(self._mem[:-1])
        except ValueError:
            return "N/A"
        if _mem > 1024:
            _mem = _mem / 1024
            return "{size}G".format(size=str(_mem))
        else:
            return "{size}M".format(size=str(_mem))

    @mem.setter
    def mem(self, val):
        self._mem = val

    def hardware(self, spec):
        """ Get hardware information

        :param spec: a hardware specification
        :type spec: str
        :returns: hardware of spec
        :rtype: str
        """
        _machine = self.machine.get('hardware', None)
        if _machine:
            _hardware_list = _machine.split(' ')
            for item in _hardware_list:
                k, v = item.split('=')
                if k in spec:
                    return v
        return 'N/A'

    @property
    def instance_id(self):
        """ Returns instance-id of a machine

        :returns: instance-id of machine
        :rtype: str
        """
        return self.machine.get('instance-id', '')

    @property
    def dns_name(self):
        """ Returns dns-name

        :rtype: str
        """
        return self.machine.get('dns-name', '')

    @property
    def agent_state(self):
        """ Returns agent-state

        :rtype: str
        """
        return self.machine.get('agent-state', '')

    @property
    def charms(self):
        """ Returns charms for machine

        :returns: charms for machine
        :rtype: generator
        """
        def charm_name(charm):
            return charm.split("/")[0]

        for unit in self.units:
            yield charm_name(unit.unit_name)

    @property
    def units(self):
        """ Return units for machine

        :rtype: list
        """
        return self.machine.get('units', [])

    @property
    def containers(self):
        """ Return containers for machine

        :rtype: generator
        """
        _containers = self.machine.get('containers', {}).items()
        for container_id, container in _containers:
            yield Machine(container_id, container)

    def container(self, container_id):
        """ Inspect a container

        :param container_id: lxc container id
        :type container_id: int
        :returns: Returns a dictionary of the container information for
                  specific machine and lxc id.
        :rtype: dict
        """
        for m in self.containers:
            if m.machine_id == container_id:
                return m
        return Machine('0/lxc/0', {'agent-state': 'unallocated',
                                   'dns-name': 'unallocated'})

    def __str__(self):
        return "id: {machine_id}, state: {state}, " \
            "dns-name: {dns_name}, mem: {mem}, " \
            "storage: {storage}, " \
            "cpus: {cpus}".format(machine_id=self.machine_id,
                                  dns_name=self.dns_name,
                                  state=self.agent_state,
                                  mem=self.mem,
                                  storage=self.storage,
                                  cpus=self.cpu_cores)

    def __repr__(self):
        return "<Machine({dns_name},{state},{mem}," \
            "{storage},{cpus})>".format(dns_name=self.dns_name,
                                        state=self.agent_state,
                                        mem=self.mem,
                                        storage=self.storage,
                                        cpus=self.cpu_cores)
