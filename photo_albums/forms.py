#coding: utf-8

import tempfile
import logging
import os

from django import forms
from django.db.models import Max
from django.forms.models import modelformset_factory
from django.utils.translation import ugettext_lazy as _
from django.core.files.uploadedfile import UploadedFile

from generic_images.models import AttachedImage
from generic_images.fields import force_recalculate

DIR_BIT = 16

# Incremental approach for unzipping files in only supported in python >= 2.6.
# Use backported zipfile.py library for python < 2.6

try:
    from zipfile import ZipFile, BadZipfile
    from zipfile import ZipExtFile # <- this will fail on python < 2.6
except ImportError:
    from photo_albums.lib.zipfile import ZipFile, BadZipfile


class ImageEditForm(forms.ModelForm):
    ''' Form for editing image captions. '''
    class Meta:
        model = AttachedImage
        fields = ['caption']

PhotoFormSet = modelformset_factory(AttachedImage, extra=3, fields = ['image', 'caption'])

class _ExistingFile(UploadedFile):
    ''' Utility class for importing existing files to FileField's. '''

    def __init__(self, path, *args, **kwargs):
        self.path = path
        super(_ExistingFile, self).__init__(*args, **kwargs)

    def temporary_file_path(self):
        return self.path

    def close(self):
        pass

    def __len__(self):
        return 0


def _file_path(uploaded_file):
    '''  Converts InMemoryUploadedFile to on-disk file so it will have path. '''
    try:
        return uploaded_file.temporary_file_path()
    except AttributeError:
        fileno, path = tempfile.mkstemp()
        temp_file = os.fdopen(fileno,'w+b')
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        temp_file.close()
        return path


class UploadZipForm(forms.Form):
    '''
        A base form class for uploading several files packed as one .zip file.
        Extract files and provides hook for processing extracted files.
        During extraction it loads uncompressed files to memory by chunks so it
        is safe to process zip archives with big files inside.
    '''

    zip_file = forms.FileField()

    def clean_zip_file(self):
        ''' Checks if zip file is not corrupted, stores in-memory uploaded file
            to disk and returns path to stored file.
        '''
        path = _file_path(self.cleaned_data['zip_file'])
        try:
            zf = ZipFile(path)
            bad_file = zf.testzip()
            if bad_file:
                raise forms.ValidationError(_('"%s" in the .zip archive is corrupt.') % bad_file)
            zf.close()
        except BadZipfile:
            raise forms.ValidationError(_('Uploaded file is not a zip file.'))

        return path


    def needs_unpacking(self, name, info):
        ''' Returns True is file should be extracted from zip and
            False otherwise. Override in subclass to customize behaviour.
            Default is to unpack all files except directories and meta files
            (names starts with '__') .
        '''
        #skip directory entries
        isdir = info.external_attr & DIR_BIT
        if isdir:
            return False

        # skip meta files
        if name.startswith('__'):
            return False

        return True


    def process_file(self, path, name, info, file_num, files_count):
        '''
        Override this in subclass to do something useful with files extracted
        from uploaded zip archive.

        Params:

        * ``path``: path to temporary file. It's on developer to delete this file.
        * ``name``: name of file in zip archive, returned by ZipFile.namelist()
        * ``info``: file info, returned by ZipFile.infolist()
        * ``file_num``: file's order number
        * ``files_count``: total files count
        '''
        raise NotImplementedError

    def process_zip_file(self, chunksize=1024*64):
        '''
            Extract all files to temporary place and call process_file method
            for each.

            ``chunksize`` is the size of block in which compressed files are
            read. Default is 64k. Do not set it below 64k because data from
            compressed files will be read in blocks >= 64k anyway.
        '''

        zip_filename = self.cleaned_data['zip_file'] #should contain zip file path

        zf = ZipFile(zip_filename)

        names = zf.namelist()
        infos = zf.infolist()

        files_to_unpack = []

        for name, info in zip(names, infos):
            if self.needs_unpacking(name, info):
                files_to_unpack.append((name, info))

        for counter, (name, info,) in enumerate(files_to_unpack):

            # extract file to temporary place
            fileno, path = tempfile.mkstemp()
            outfile = os.fdopen(fileno,'w+b')

            stream = zf.open(info)
            while True:
                hunk = stream.read(chunksize)
                if not hunk:
                    break
                outfile.write(hunk)

            outfile.close()

            # do something with extracted file
            self.process_file(path, name, info, counter, len(files_to_unpack))

        zf.close()
        os.unlink(zip_filename)


class UploadZipAlbumForm(UploadZipForm):
    ''' Form for uploading several images packed as one .zip file.
        Only valid images are stored. Uploaded images are marked as uploaded
        by ``user`` and are attached to ``obj`` model.
    '''
    def __init__(self, user, obj, *args, **kwargs):
        super(UploadZipAlbumForm, self).__init__(*args, **kwargs)

        self.user = user
        self.obj = obj
        self.order = AttachedImage.objects.for_model(obj).aggregate(max_order=Max('order'))['max_order']

        self.fields['zip_file'].label = _('images file (.zip)')
        self.fields['zip_file'].help_text = _('Select a .zip file of images to upload.')



    def needs_unpacking(self, name, info):
        ''' Returns True is file should be extracted from zip and
            False otherwise. Override in subclass to customize behaviour.
            Default is to skip directories, meta files
            (names starts with ``'__'``) and files with non-image extensions.
        '''
        for ext in ['.jpg', '.jpeg', '.png', '.gif']:
            if name.lower().endswith(ext):
                return super(UploadZipAlbumForm, self).needs_unpacking(name, info)
        return False


    def is_valid_image(self, path):
        ''' Check if file is readable by PIL. '''
        from PIL import Image

        try:
            trial_image = Image.open(path)
            trial_image.verify()
        except ImportError:
            # Under PyPy, it is possible to import PIL. However, the underlying
            # _imaging C module isn't available, so an ImportError will be
            # raised. Catch and re-raise.
            raise
        except Exception: # Python Imaging Library doesn't recognize it as an image
            return False

        return True


    def process_file(self, path, name, info, file_num, files_count):
        ''' Create AttachedImage instance if file is a valid image. '''

        # flatten directories
        fname = os.path.split(name)[1]

        # only process valid images
        if self.is_valid_image(path):
            self.order += 1
            image = AttachedImage(user = self.user, caption = '',
                                  order = self.order, content_object = self.obj)

            # do not generate tons of SQL queries
            image.send_signal = False
            image.get_file_name = lambda filename: str(self.order)

            # Move file to proper place (without copying if it is possible) and
            # create record in database
            image.image.save(image.get_upload_path(fname), _ExistingFile(path))
        else:
            # image is invalid, we should delete temp file
            os.unlink(path)

        # Because ImageCountField fields where disabled we have to
        # recalculate denormalised values
        is_last = (file_num == (files_count-1))
        if is_last:
            force_recalculate(self.obj)
