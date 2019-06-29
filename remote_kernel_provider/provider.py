"""Provides base support to various remote kernel providers."""

import os
import re

from .manager import RemoteKernelManager
from jupyter_kernel_mgmt.discovery import KernelSpecProvider
from traitlets.log import get_logger as get_app_logger
from traitlets.config import Application

log = get_app_logger()  # We should always be run within an application


class RemoteKernelProviderBase(KernelSpecProvider):

    # The following must be overridden by subclasses
    id = None
    lifecycle_manager_class = None

    def launch(self, kernelspec_name, cwd=None, kernel_params=None):
        """Launch a kernel, return (connection_info, kernel_manager).

        name will be one of the kernel names produced by find_kernels()

        This method launches and manages the kernel in a blocking manner.
        """
        kernelspec = self.ksm.get_kernel_spec(kernelspec_name, provider_id=self.id)
        lifecycle_info = self._get_lifecycle_info(kernelspec)
        if lifecycle_info is None:
            raise RuntimeError("Lifecycle manager information could not be found in kernel.json file for kernel '{}'!  "
                               "Check the kernel.json file located at '{}' and try again.".
                               format(kernelspec_name, kernelspec.resource_dir))

        # Make the appropriate application configuration (relative to provider) available during launch
        app_config = self._get_app_config()

        # Launch the kernel via the kernel manager class method, returning its connection information
        # and kernel manager.
        kwargs = dict()
        kwargs['kernelspec'] = kernelspec
        kwargs['lifecycle_info'] = lifecycle_info
        kwargs['cwd'] = cwd
        kwargs['kernel_params'] = kernel_params or {}
        kwargs['app_config'] = app_config
        return RemoteKernelManager.launch(**kwargs)

    def launch_async(self, name, cwd=None):
        pass

    def _get_app_config(self):
        """Pulls application configuration 'section' relative to current class."""

        app_config = {}
        parent_app = Application.instance()
        if parent_app:
            # Collect config relative to our class instance.
            app_config = parent_app.config.get(self.__class__.__name__, {}).copy()
        return app_config

    def _get_lifecycle_info(self, kernelspec):
        """Looks for the metadata stanza containing the lifecycle manager information.
           This will be in the `lifecycle_manager` stanza of the metadata.

           Since the only way this provider will be called to launch a kernel is
           due to the fact that provider_id exists in the kernel.json, we can assume
           that the metadata stanza and process proxy class names have also been
           updated - so we'll forgo checks for legacy entries.
        """
        lifecycle_info = kernelspec.metadata.get('lifecycle_manager', None)
        if lifecycle_info:
            class_name = lifecycle_info.get('class_name', None)
            if class_name is not None and class_name == self.lifecycle_manager_class:
                if 'config' not in lifecycle_info:  # if no config stanza, add one for consistency
                    lifecycle_info.update({"config": {}})
            else:
                lifecycle_info = None

        return lifecycle_info
