#coding: utf-8
'''
    django-photo-albums provides base class (photo_albums.test_utils.AlbumTest) 
    for writing integration tests for app instances. 
    
    The example usage::
    
        from accounts.urls import accounts_photo_site
        from photo_albums import test_utils
        
        class UserAlbumTest(test_utils.AlbumTest):
            # existing user's data
            username = 'obiwanus' 
            password = 'vasia'
            
            # fixtures to be loaded (at least with users, images and 
            # objects with galleries)
            fixtures = ['my_fixtures']
            
            # app instance which is to be tested
            album_site = accounts_photo_site
            
            # we don't need edit_image view and don't create template for it
            # so it should be excluded from testing
            excluded_views = ['edit_image']
            
            # id of object for which album is attached
            album_for_id = 4
                        
            # if slugs are in use:
            # album_for_id = 'my_object_slug'
            
            # if object_getter is in use:
            # album_for_kwargs = {'year': 2009, 'month': 12, 'day': 5, 'slug': 'wow'}                        
            
            # id's of various images: 2 images in album (second is nedded if you
            # want to test reordering) and one image in other album to test
            # permission checks
            image_in_album_id = 48
            image2_in_album_id = 66
            image_in_other_album_id = 42    
                
    If you don't use fixtures you can override setUp method and create necessery 
    objects there. 
    
'''

from django.core.urlresolvers import reverse, NoReverseMatch
from generic_utils.test_helpers import ViewTest
from generic_images.models import AttachedImage

class AlbumTest(ViewTest):
        
    username = None
    "existing user's username"

    password = None
    "existing user's password"
    
    fixtures = []
    """ fixtures to be loaded (at least with users, images and
        objects with galleries)
    """
    
    album_site = None
    " ``PhotoAlbumSite`` instance to be tested "
    
    excluded_views = []
    " a list of names of excluded views. Excluded views won't be tested. "
    
    album_for_id = None
    " object id (or slug) for which album is attached to "
    
    album_for_kwargs = None
    "object url resolver kwargs (for more complex object urls)"    
    
    non_existing_object_id = 0
    
    non_existing_object_kwargs = None
    
    image2_in_album_id = None    
    " "
    
    image_in_album_id = None
    " "
    
    image_in_other_album_id = None
    """ id's of various images: 2 images in album (second is nedded if tou 
        want to test reordering) and one image in other album to test 
        permission checks
    """
    
    non_existing_image_id = 0
    
    def __init__(self, *args, **kwargs):
        if (self.album_for_id is not None) and (self.album_for_kwargs is not None):
            raise ValueError('Ambiguity between album_for_id and '
                             'album_for_kwargs. Please remove one of these parameters.')
            
        if self.non_existing_object_kwargs is None: 
            self.non_existing_object_kwargs = {'object_id':self.non_existing_object_id}
            
        super(AlbumTest, self).__init__(*args, **kwargs)
        
        
    
    def check(self, view, status, kwargs=None):
        if not kwargs:
            kwargs = {}
        if view not in self.excluded_views:            
            name = '%s:%s' % (self.album_site.instance_name, view,)
            if self.album_for_id is not None:                
                if not 'object_id' in kwargs:
                    kwargs['object_id'] = self.album_for_id
            else:
                if kwargs != self.non_existing_object_kwargs:
                    kwargs.update(self.album_for_kwargs)
            return self.check_url(name, status, kwargs=kwargs, current_app=self.album_site.app_name)                
                
    def test_public_views(self):
        self.check('show_album', 200)
        
        try:
            self.check('show_album', 404, kwargs=self.non_existing_object_kwargs)
        except NoReverseMatch: # non_existing_object_kwargs is needed but not specified, 
            pass               # don't want to force all developers to add this just for one small test

        self.check('show_image', 200, kwargs={'image_id': self.image_in_album_id})
        self.check('show_image', 404, kwargs={'image_id': self.image_in_other_album_id})
        self.check('show_image', 404, kwargs={'image_id': self.non_existing_image_id})
        
    def test_forbidden_views(self):
        self.check('edit_album', 302)
        self.check('upload_main_image', 302)
        self.check('upload_images', 302)
        self.check('edit_image', 302, kwargs={'image_id': self.image_in_album_id})
        self.check('delete_image', 302, kwargs={'image_id': self.image_in_album_id})
        self.check('set_as_main_image', 302, kwargs={'image_id': self.image_in_album_id})
        self.check('clear_main_image', 302, kwargs={'image_id':  self.image_in_album_id})
        self.check('set_image_order', 302)
        
    def test_auth_views(self):
        self.assertTrue(self.client.login(username=self.username, password=self.password))

        self.check('edit_album', 200)
        self.check('upload_main_image', 200)
        self.check('upload_images', 200)
        self.check('show_album', 200)
        self.check('show_image', 200, kwargs={'image_id': self.image_in_album_id})
        
        self.check('reorder_images', 200)
        self.check('set_image_order', 404)

        self.check('edit_image', 200, kwargs={'image_id': self.image_in_album_id})
        self.check('delete_image', 200, kwargs={'image_id': self.image_in_album_id})
        self.check('set_as_main_image', 302, kwargs={'image_id': self.image_in_album_id})
        self.check('clear_main_image', 302, kwargs={'image_id': self.image_in_album_id})

    def test_reorder(self):
        if self.image2_in_album_id is None:
            return

        name = '%s:%s' % (self.album_site.instance_name, 'set_image_order',)
        url = reverse(name, kwargs={'object_id': self.album_for_id}, current_app = self.album_site.app_name)   
        
        img1 = AttachedImage.objects.get(id=self.image_in_album_id)
        img2 = AttachedImage.objects.get(id=self.image2_in_album_id)

        #correct:
        self.assertTrue(self.client.login(username=self.username, password=self.password))
        response = self.client.post(url, 
                                   {'items': '[{"id":"%d","order":"%d"},{"id":"%d","order":"%d"}]' % 
                                               (img1.id, img2.order,img2.id, img1.order)}, 
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.content, '{"done": true}')
        
        img1_new = AttachedImage.objects.get(id=self.image_in_album_id)
        img2_new = AttachedImage.objects.get(id=self.image2_in_album_id)
        
        self.assertEqual(img1_new.id, img1.id)
        self.assertEqual(img1_new.order, img2.order)
        self.assertEqual(img2_new.id, img2.id)        
        self.assertEqual(img2_new.order, img1.order)