# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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


class BaitUser(object):
    """This class provides an abstraction to represent a user within
       the Honeypot."""

    def __init__(self, username, password):

        self.username = username
        self.password = password

        # This and all other paths defined for this class are relative to the vfs.
        # These strings (paths) are later used by the Handlers for each capability
        # to generate new fs.osfs.OSFS instances, which help manage the data for
        # that particular capability.
        self.http_dir = '/var/www'
        self.ftp_dir = '/var/pub/ftp/' + self.username
        self.mail_dir = '/var/spool/mail' + self.username
        self.home_dir = '/home/' + self.username

    def get_password(self):
        return self.password
