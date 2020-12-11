import os
from hashlib import sha1

from django.utils.encoding import smart_str

from mediagenerator.utils import find_file, load_backend, read_text_file

from .settings import DEFAULT_MEDIA_FILTERS


class Filter:
    takes_input = True

    def __init__(self, **kwargs):
        self.file_filter = FileFilter
        self.config(kwargs,
                    filetype=None, filter=None,
                    bundle=None, _from_default=None)

        # We assume that if this is e.g. a 'js' backend then all input must
        # also be 'js'. Subclasses must override this if they expect a special
        # input file type. Also, subclasses have to check if their file type
        # is supported.
        self.input_filetype = self.filetype

        if self.takes_input:
            self.config(kwargs, input=())
            if not isinstance(self.input, (tuple, list)):
                self.input = (self.input,)
        self._input_filters = None
        assert not kwargs, 'Unknown parameters: {}'.format(', '.join(kwargs.keys()))

    @classmethod
    def from_default(cls, name):
        return {'input': name}

    def should_use_default_filter(self, ext):
        return ext != self._from_default

    def get_variations(self):
        """
        Returns all possible variations that get generated by this filter.

        The result must be a dict whose values are tuples.
        """
        return {}

    def get_output(self, variation):
        """
        Yields content for each output item for the given variation.
        """
        raise NotImplementedError()

    def get_dev_output(self, name, variation):
        """
        Returns content for the given file name and variation in development mode.
        """
        index, child = name.split('/', 1)
        index = int(index)
        filter = self.get_input_filters()[index]
        return filter.get_dev_output(child, variation)

    def get_dev_output_names(self, variation):
        """
        Yields file names for the given variation in development mode.
        """
        # By default we simply return our input filters' file names
        for index, filter in enumerate(self.get_input_filters()):
            for name, hash in filter.get_dev_output_names(variation):
                yield f'{index}/{name}', hash

    def get_input(self, variation):
        """Yields contents for each input item."""
        for filter in self.get_input_filters():
            for input in filter.get_output(variation):
                yield input

    def get_input_filters(self):
        """Returns a Filter instance for each input item."""
        if not self.takes_input:
            raise ValueError(
                "The {} media filter doesn't take any input".format(
                    self.__class__.__name__,
                ))

        if self._input_filters is not None:
            return self._input_filters

        self._input_filters = []

        for input in self.input:
            if isinstance(input, dict):
                filter = self.get_filter(input)
            else:
                filter = self.get_item(input)

            self._input_filters.append(filter)

        return self._input_filters

    def get_filter(self, config):
        backend_class = load_backend(config.get('filter'))
        return backend_class(filetype=self.input_filetype, bundle=self.bundle,
                             **config)

    def get_item(self, name):
        ext = os.path.splitext(name)[1].lstrip('.')
        if ext in DEFAULT_MEDIA_FILTERS and self.should_use_default_filter(ext):
            backend_class = load_backend(DEFAULT_MEDIA_FILTERS[ext])
        else:
            backend_class = self.file_filter

        config = backend_class.from_default(name)
        config.setdefault(
            'filter',
            f'{backend_class.__module__}.{backend_class.__name__}',
        )
        config.setdefault('filetype', self.input_filetype)
        config['bundle'] = self.bundle
        # This is added to make really sure we don't instantiate the same
        # filter in an endless loop. Normally, the child class should
        # take care of this in should_use_default_filter().
        config.setdefault('_from_default', ext)

        return backend_class(**config)

    def _get_variations_with_input(self):
        """Utility function to get variations including input variations"""
        variations = self.get_variations()
        if not self.takes_input:
            return variations

        for filter in self.get_input_filters():
            subvariations = filter._get_variations_with_input()
            for k, v in subvariations.items():
                if k in variations and v != variations[k]:
                    raise ValueError(
                        'Conflicting variations for "{}": {!r} != {!r}'.format(
                            k, v, variations[k],
                        ))
            variations.update(subvariations)
        return variations

    def config(self, init, **defaults):
        for key in defaults:
            setattr(self, key, init.pop(key, defaults[key]))


class FileFilter(Filter):
    """A filter that just returns the given file."""
    takes_input = False

    def __init__(self, **kwargs):
        self.config(kwargs, name=None)
        self.mtime = self.hash = None
        super().__init__(**kwargs)

    @classmethod
    def from_default(cls, name):
        return {'name': name}

    def get_output(self, variation):
        yield self.get_dev_output(self.name, variation)

    def get_dev_output(self, name, variation):
        assert name == self.name, (
            f'''File name "{name}" doesn't match the one in GENERATE_MEDIA ("{self.name}")'''
        )
        return read_text_file(self._get_path())

    def get_dev_output_names(self, variation):
        path = self._get_path()
        mtime = os.path.getmtime(path)
        if mtime != self.mtime:
            output = self.get_dev_output(self.name, variation)
            hash = sha1(smart_str(output)).hexdigest()
        else:
            hash = self.hash
        yield self.name, hash

    def _get_path(self):
        path = find_file(self.name)
        assert path, f"""File name "{self.name}" doesn't exist."""
        return path


class RawFileFilter(FileFilter):
    takes_input = False

    def __init__(self, **kwargs):
        self.config(kwargs, path=None)
        super().__init__(**kwargs)

    def get_dev_output(self, name, variation):
        assert name == self.name, (
            f'''File name "{name}" doesn't match the one in GENERATE_MEDIA ("{self.name}")''')
        return read_text_file(self.path)

    def get_dev_output_names(self, variation):
        mtime = os.path.getmtime(self.path)
        if mtime != self.mtime:
            output = self.get_dev_output(self.name, variation)
            hash = sha1(smart_str(output)).hexdigest()
        else:
            hash = self.hash

        yield self.name, hash


class SubProcessFilter(Filter):
    class ProcessError(Exception):
        def __init__(self, message, stderr='', stdout='', retcode=0):
            super().__init__(message)
            self.stderr = stderr
            self.stdout = stdout
            self.retcode = retcode

    def run_process(self, command, input=None):
        # We import this here, so App Engine Helper users don't get import errors.
        from subprocess import PIPE, Popen

        # universal_newlines enables text mode for stdin. That cause an issue
        # in windows which use cp1252 as default for western europe.
        #
        # The "encoding" argument in python 3.6 fix it by forcing the
        # right encoding to io.TextIOWrapper (see Popen code).
        #
        # # In python 3.5 removing universal_newlines and encode input as utf-8
        # # bytes fix the problem in a different way.
        # if sys.version_info < (3, 6):
        #     cmd = Popen(command,
        #                 stdin=PIPE, stdout=PIPE, stderr=PIPE)
        #     output, error = cmd.communicate(input.encode('utf-8'))
        # else:
        #     cmd = Popen(command,
        #                 stdin=PIPE, stdout=PIPE, stderr=PIPE, encoding='utf-8',
        #                 universal_newlines=True)
        #     output, error = cmd.communicate(input)
        cmd = Popen(command,
                    stdin=PIPE, stdout=PIPE, stderr=PIPE, encoding='utf-8',
                    universal_newlines=True,
                   )
        output, error = cmd.communicate(input)
        retcode = cmd.wait()

        if retcode != 0:
            raise self.ProcessError(
                'Command returned bad result',
                stderr=error,
                stdout=output,
                retcode=retcode
            )

        return output

    def format_lint_errors(self, errors, source, context=2):
        lines = source.splitlines()
        count = len(lines)
        output = []

        for index, col, message in errors:
            start = max(0, index - context - 1)
            end = min(index + context, count)

            output.append('______________________________________________')
            output.extend(f'{num:>6d}: {line}' for num, line in enumerate(
                lines[start:index], start + 1
            ))
            output.append(f'        {col*" "}^__ {message}\n')
            output.extend(f'{num:>6d}: {line}' for num, line in enumerate(
                lines[index:end], index + 1
            ))
            output.append('')

        return '\n'.join(output)
