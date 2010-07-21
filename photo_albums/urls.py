#coding: utf-8
'''
    To add image gallery for your model you should complete following steps:

    1. Create album site instance and plug it's urls to urlconf::

        from photo_albums.urls import PhotoAlbumSite
        accounts_photo_site = PhotoAlbumSite(instance_name = 'user_images',
                                 queryset = User.objects.all(),
                                 template_object_name = 'album_user',
                                 has_edit_permission = lambda request, obj: request.user==obj)
        urlpatterns += patterns('', url(r'^accounts/', include(accounts_photo_site.urls)),)

    Please note that if you deploy multiple albums (ex. for different models),
    you must provide unique ``instance_name`` for each instance to make url
    reversing work.

    Included urls looks like ``<object_id>/<app_name>/<action>`` or
    ``<object_id>/<app_name>/<image_id>/<action>``,
    where object_id is the id of object which is gallery attached to,
    app_name is "album" by default (you can change it :ref:`here<app_name_param>`),
    image_id is image id :-) and action is the performed action (view, edit, etc).
    It is possible to use slug instead of object's id
    (look at ``object_regex`` and ``lookup_field`` :ref:`parameters<custom_url_scheme>`).

    It is also possible to attach PhotoAlbumSite to any url using
    :ref:`object_getter<object_getter>` parameter.

    2. Create the necessary templates.

    3. Link people to image gallery using ``{% url .. %}`` template tags.

    You can use these urls (assuming that ``user_images`` is an instance name,
    ``album_user`` is the object for which gallery is attached to, ``image`` is an image
    in gallery and slugs are not used)::

        {% url user_images:show_album album_user.id %}

        {% url user_images:edit_album album_user.id %}

        {% url user_images:upload_main_image album_user.id %}

        {% url user_images:upload_images album_user.id %}

        {% url user_images:upload_zip album_user.id %}

        {% url user_images:show_image album_user.id image.id %}

        {% url user_images:edit_image album_user.id image.id %}

        {% url user_images:delete_image album_user.id image.id %}

        {% url user_images:set_as_main_image album_user.id image.id %}

        {% url user_images:clear_main_image album_user.id image.id %}

        {% url user_images:reorder_images album_user.id %}

        {% url user_images:set_image_order album_user.id %}

'''

from django.conf.urls.defaults import *
from generic_utils.app_utils import PluggableSite
from photo_albums.forms import ImageEditForm, PhotoFormSet, UploadZipAlbumForm
from generic_images.forms import AttachedImageForm

class PhotoAlbumSite(PluggableSite):
    '''
    Constructor parameters:

    ``instance_name``: String. Required. App instance name for url
    reversing. Must be unique.

    ``queryset``: QuerySet. Required. Albums will be attached to objects
    in this queryset.

    .. _custom_url_scheme:

    ``object_regex``: String. Optional, default is ``'\d+'``. It should be a
    URL regular expression for object in URL. You should use smth.
    like ``'[\w\d-]+'`` for slugs.

    ``lookup_field``: String. Optional, default is ``'pk'``. It is a field
    name to lookup. It may contain ``__`` and follow relations
    (ex.: ``userprofile__slug``).

    .. _app_name_param:

    ``app_name``: String. Optional, default value is ``'album'``. Used by url
    namespaces stuff.

    ``extra_context``: Dict. Optional. Extra context that will be passed
    to each view.

   .. _template_object_name:

    ``template_object_name``: String. Optional. The name of template
    context variable with object for which album is attached.
    Default is ``'object'``.

    ``has_edit_permission``: Optional. Function that accepts request and
    object and returns True if user is allowed to edit album for
    object and False otherwise. Default behaviour is to always
    return True.

    ``context_processors``: Optional. A list of callables that will be
    used as additional context_processors in each view.

    .. _object_getter:

    ``object_getter``: special function that returns object that PhotoAlbumSite
    is attached to. It is special because it must have
    explicitly assigned 'regex' attribute. This regex will be passed to django
    URL system. Parameters from this regex will be then passed to object_getter
    function.

    Example::

        def get_place(city_slug, place_slug):
            return Place.objects.get(city__slug=city_slug, slug=place_slug)
        get_place.regex = r'(?P<city_slug>[\w\d-]+)/(?P<place_slug>[\w\d-]+)'


    .. _edit_form_class:

    ``edit_form_class``: Optional, default is
    :class:`~photo_albums.forms.ImageEditForm`. ModelForm subclass to be used in
    :func:`~photo_albums.views.edit_image` view.

    .. _upload_form_class:

    ``upload_form_class``: Optional, default is ``AttachedImageForm`` (defined in
    ``generic_images.forms`` module). ModelForm subclass to be used in
    :func:`~photo_albums.views.upload_main_image` view.

    .. _upload_formset_class:

    ``upload_formset_class``: Optional, default is
    :ref:`PhotoFormSet<photoformset>`. ModelFormSet to be used in
    :func:`~photo_albums.views.upload_images` view.

    .. _upload_zip_form_class:

    ``upload_zip_form_class``: Optional, default is
    :class:`~photo_albums.forms.UploadZipAlbumForm`. Form to be used in
    :func:`~photo_albums.views.upload_zip` view.

    '''
    def __init__(self,
                 instance_name,
                 app_name = 'album',
                 queryset = None,
                 object_regex = None,
                 lookup_field = None,
                 extra_context=None,
                 template_object_name = 'object',
                 has_edit_permission = lambda request, obj: True,
                 context_processors = None,
                 object_getter = None,
                 edit_form_class = ImageEditForm,
                 upload_form_class = AttachedImageForm,
                 upload_formset_class = PhotoFormSet,
                 upload_zip_form_class = UploadZipAlbumForm
                ):

        self.edit_form_class = edit_form_class
        self.upload_form_class = upload_form_class
        self.upload_formset_class = upload_formset_class
        self.upload_zip_form_class = upload_zip_form_class

        super(PhotoAlbumSite, self).__init__(instance_name, app_name, queryset,
                                             object_regex, lookup_field,
                                             extra_context, template_object_name,
                                             has_edit_permission, context_processors,
                                             object_getter)

    def patterns(self):
        return patterns('photo_albums.views',

                        #album-level views
                        url(
                            self.make_regex(r'/'),
                            'show_album',
                            {'album_site': self},
                            name = 'show_album',
                        ),
                        url(
                            self.make_regex(r'/edit/'),
                            'edit_album',
                            {'album_site': self},
                            name = 'edit_album',
                        ),
                        url(
                            self.make_regex(r'/upload-main/'),
                            'upload_main_image',
                            {'album_site': self},
                            name = 'upload_main_image',
                        ),
                        url(
                            self.make_regex(r'/upload-images/'),
                            'upload_images',
                            {'album_site': self},
                            name = 'upload_images',
                        ),
                        url(
                            self.make_regex(r'/upload-zip/'),
                            'upload_zip',
                            {'album_site': self},
                            name = 'upload_zip',
                        ),


                        #one image views
                        url(
                            self.make_regex(r'/(?P<image_id>\d+)/'),
                            'show_image',
                            {'album_site': self},
                            name = 'show_image',
                        ),
                        url(
                            self.make_regex(r'/(?P<image_id>\d+)/edit/'),
                            'edit_image',
                            {'album_site': self},
                            name = 'edit_image',
                        ),
                        url(
                            self.make_regex(r'/(?P<image_id>\d+)/delete/'),
                            'delete_image',
                            {'album_site': self},
                            name = 'delete_image',
                        ),
                        url(
                            self.make_regex(r'/(?P<image_id>\d+)/set-as-main/'),
                            'set_as_main_image',
                            {'album_site': self},
                            name = 'set_as_main_image',
                        ),
                        url(
                            self.make_regex(r'/(?P<image_id>\d+)/clear-main/'),
                            'clear_main_image',
                            {'album_site': self},
                            name = 'clear_main_image',
                        ),

                        #reorder
                        url(
                            self.make_regex(r'/reorder/'),
                            'edit_album',
                            {'album_site': self, 'template_name': 'reorder_images.html'},
                            name = 'reorder_images',
                        ),
                        url(
                            self.make_regex(r'/set-image-order'),
                            'set_image_order',
                            {'album_site': self},
                            name = 'set_image_order',
                        ),
                    )

