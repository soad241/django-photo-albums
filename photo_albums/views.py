'''
Views used by PhotoAlbumSite.
'''

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.generic.create_update import delete_object
from django.utils import simplejson
from django.core.paginator import Paginator

from annoying.decorators import ajax_request
from annoying.utils import HttpResponseReload

from generic_images.models import AttachedImage
from generic_utils import get_template_search_list
from generic_utils.app_utils import get_site_decorator

# decorator for AlbumSite views
album_site_method = get_site_decorator('album_site')

# a couple of functions to make templates rendering easier
def _get_template_names(object, template_name):
    return get_template_search_list('albums', object, template_name)

def _render(template, obj, context):
    template_variants = _get_template_names(obj, template)
    return render_to_response(template_variants, context_instance=context)

def get_prepared_errors(form):
    return dict([(unicode(f), unicode(form.errors[f][0]),) for f in form.errors]) #todo: get rif of errors[f][0]


#==============================================================================

@album_site_method(template_name='show_album.html')
def show_album(request, obj, album_site, context, template_name):
    ''' Show album for object using show_album.html template '''

    images = AttachedImage.objects.for_model(obj)
    context.update({'images': images})

    return _render(template_name, obj, context)



@login_required
@album_site_method(template_name='edit_album.html')
def edit_album(request, obj, album_site, context, template_name):
    ''' Show album for object using edit_album.html template, with permission checks. '''

    album_site.check_permissions(request, obj)

    images = AttachedImage.objects.for_model(obj)
    context.update({'images': images})

    return _render(template_name, obj, context)


@login_required
@ajax_request
@album_site_method()
def upload_main_image(request, obj, album_site, context):
    ''' Upload 1 image and make it main image in gallery '''

    album_site.check_permissions(request, obj)
    success_url = '../' #album_site.reverse('show_album', args=[object_id])
    if request.method == 'POST':
        form = album_site.upload_form_class(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)     #TODO: move logic to form
            photo.user = request.user
            photo.content_object = obj
            photo.is_main = True
            photo.save()
            if request.is_ajax():
                return HttpResponse()
            return HttpResponseRedirect(success_url) # Redirect after POST
        else:
            if request.is_ajax():
                return get_prepared_errors(form)
    else:
        form = album_site.upload_form_class()

    if request.is_ajax():
        return HttpResponse()

    context.update({'form': form})
    return _render('upload_main_image.html', obj, context)


@login_required
@ajax_request
@album_site_method()
def upload_zip(request, obj, album_site, context):
    ''' Upload zip archive with images, extract them, check if they are correct
        and attach to object. Redirect to ``show_album`` view on success.
    '''
    album_site.check_permissions(request, obj)

    form_class = album_site.upload_zip_form_class

    if request.method == 'POST':
        form = form_class(request.user, obj, request.POST, request.FILES)
        if form.is_valid():
            form.process_zip_file()
            success_url = '../' #album_site.reverse('show_album', args=[object_id])
            if request.is_ajax():
                return HttpResponse()
            return HttpResponseRedirect(success_url)
        else:
            if request.is_ajax():
                return get_prepared_errors(form)
    else:
        form = form_class(request.user, obj)

    if request.is_ajax():
        return HttpResponse()

    context.update({'form': form})

    return _render('upload_zip.html', obj, context)

@login_required
@ajax_request
@album_site_method()
def upload_images(request, obj, album_site, context):
    ''' Upload several images at once '''

    album_site.check_permissions(request, obj)

    success_url = '../' # album_site.reverse('show_album', args=[object_id])

    FormsetCls = album_site.upload_formset_class

    if request.method == 'POST':
        formset = FormsetCls(request.POST,
                             request.FILES,
                             queryset = AttachedImage.objects.none())
        if formset.is_valid():
            instances = formset.save(commit=False)
            for photo in instances:
                photo.user = request.user
                photo.content_object = obj
                photo.save()
            if request.is_ajax():
                return HttpResponse()
            return HttpResponseRedirect(success_url) # Redirect after POST
        else:
            if request.is_ajax():
                return get_prepared_errors(formset)
    else:
        formset = FormsetCls(queryset = AttachedImage.objects.none())

    context.update({'formset': formset})

    return _render('upload_images.html', obj, context)


def _one_image_context(image_id, obj):
    album = AttachedImage.objects.for_model(obj)
    image = get_object_or_404(album, id=image_id)

    next_id = getattr(image.next(), 'id', None)
    prev_id = getattr(image.previous(), 'id', None)

    return {'image': image, 'prev': prev_id, 'next': next_id}


@album_site_method(image_id=None)
def show_image(request, obj, album_site, context, image_id):
    '''  Show one image '''
    context.update(_one_image_context(image_id, obj))
    return _render('show_image.html', obj, context)


@login_required
@album_site_method(image_id=None)
def edit_image(request, obj, album_site, context, image_id):
    ''' Show one image. Checks permissions and provides edit form. '''

    album_site.check_permissions(request, obj)
    context.update(_one_image_context(image_id, obj))

    FormCls = album_site.edit_form_class

    if request.method == 'POST':
        form = FormCls(request.POST, request.FILES, instance = context['image'])
        if form.is_valid():
            form.save()
            return HttpResponseReload(request) # Redirect after POST
    else:
        form = FormCls(instance = context['image'])

    context.update({'form': form})

    return _render('edit_image.html', obj, context)


@login_required
@album_site_method(image_id=None)
def delete_image(request, obj, album_site, context, image_id):
    ''' Delete image if request method is POST, displays
        ``confirm_delete.html`` template otherwise
    '''
    album_site.check_permissions(request, obj)

    image = get_object_or_404(AttachedImage.objects.for_model(obj), id=image_id)
    next_url = '../../' #album_site.reverse('show_album', args=[object_id])

    plain_context = {}
    for d in context:
        plain_context.update(d)

    return delete_object(request,
                         model=AttachedImage,
                         post_delete_redirect = next_url,
                         object_id = image_id,
                         extra_context = plain_context,
                         context_processors=album_site.context_processors,
                         template_name = _get_template_names(obj, 'confirm_delete.html')[1])


@login_required
@album_site_method(image_id=None)
def set_as_main_image(request, obj, album_site, context, image_id):
    ''' Mark image as main and redirect to ``show_image`` view '''
    album_site.check_permissions(request, obj)

    image = get_object_or_404(AttachedImage.objects.for_model(obj), id=image_id)
    image.is_main = True
    image.save()

    return HttpResponseRedirect('../')


@login_required
@album_site_method(image_id=None)
def clear_main_image(request, obj, album_site, context, image_id):
    ''' Mark image as not main and redirect to ``show_image`` view '''
    album_site.check_permissions(request, obj)

    image = AttachedImage.objects.get_main_for(obj)
    if image:
        image.is_main = False
        image.save()

    return HttpResponseRedirect('../')


@login_required
@ajax_request
@album_site_method()
def set_image_order(request, obj, album_site, context):
    ''' Ajax view that can be used to implement image reorder
    functionality. Accepts json data in form::

        {'items': '[
                        {"id":"<id1>", "order":"<order1>"},
                        {"id":"<id2>", "order":"<order2>"},
                        ...
                    ]'
        }

    and assigns passed order to images with passed id's, with permission checks.
    '''
    album_site.check_permissions(request, obj)

    if request.is_ajax():
        data_str = request.POST.get('items','')
        items = simplejson.loads(data_str)
        for item in items:
            image_id = item['id']
            order = item['order']
            try:
                #check that image belongs to proper object
                image = AttachedImage.objects.for_model(obj).get(id=image_id)
                image.order = order
                image.save()
            except AttachedImage.DoesNotExist:
                return {'done': False, 'reason': 'Invalid data.'}
        return {'done': True}
    raise Http404
