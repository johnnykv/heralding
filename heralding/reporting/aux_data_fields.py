# Copyright (C) 2019 Sudipta Pandit <realsdx@protonmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


class AuxiliaryData:
    fields = {
        'ssh': ['client_version', 'recv_cipher', 'recv_mac']
    }

    @staticmethod
    def get_logfile_name(protocol_name):
        return 'aux_'+protocol_name+'.csv'

    @staticmethod
    def get_filelog_fields(protocol_name):
        default_fields = ['timestamp', 'session_id', 'protocol']
        protocol_fields = AuxiliaryData.fields.get(protocol_name)
        return default_fields+protocol_fields

    @staticmethod
    def get_data_fields(protocol_name):
        return AuxiliaryData.fields.get(protocol_name)
