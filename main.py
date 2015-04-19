import uuid
import cgi
import webapp2
import logging
import os


from google.appengine.api import app_identity
from google.appengine.ext import ndb
from webapp2_extras import sessions
from google.appengine.api import mail

import cloudstorage import gcs

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import cgitb
cgitb.enable()

MAIL_STR = 'Sayın, {0}<br>Hesabınızı Aktifleştirmek için <a href="{1}/Activasyon?key={2}" >Buraya Tıklayınız</a>'

my_default_retry_params = '' #gcs.RetryParams(initial_delay=0.2,max_delay=5.0,backoff_factor=2,max_retry_period=15)
										  
#gcs.set_default_retry_params(my_default_retry_params)
bucket_name = 'aloboxdeneme'

class User(ndb.Model):
	userid = ndb.IntegerProperty()
	name = ndb.StringProperty()
	mail = ndb.StringProperty()
	password = ndb.StringProperty()
	activ_key = ndb.StringProperty()
	activ = ndb.BooleanProperty()

class FileList(ndb.Model):
	userid = ndb.IntegerProperty()
	name = ndb.StringProperty()
	size = ndb.FloatProperty()
	loadtime = ndb.DateTimeProperty()
	c_position = ndb.StringProperty()
	deleted = ndb.BooleanProperty()

class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        self.session_store = sessions.get_store(request=self.request)

        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session()
	
class MainHandler(BaseHandler):
    def get(self):
		#for u in User.query():
		#	u.key.delete()
		if self.session.get('userid') != None :
			self.redirect('/dashboard')
		file = open("index.html");
		self.response.out.write(file.read())

class Signup(BaseHandler):
    def post(self):
		ac_kod = str(uuid.uuid4())
		user = User(name = cgi.escape(self.request.get('firstname')),
					mail = cgi.escape(self.request.get('mail')),
					password = cgi.escape(self.request.get('password')),
					activ_key = ac_kod,
					activ = False)
		user.put()
		
		message = mail.EmailMessage(sender="Alo box <birisi999@gmail.com>", subject = "Hesap Aktivasyonu")
		message.to =  '<' + user.mail + '>'

		message.body =  MAIL_STR.format(user.name,self.request.host_url, user.activ_key)
		message.html =  MAIL_STR.format(user.name,self.request.host_url, user.activ_key)
		message.send()
		
		self.response.out.write('Hesabınız oluşturulmuştur. Activasyon için E-Posta Gelen Kutunuzu kontrol ediniz');
		#file = open("signup.html");
		#self.response.out.write(file.read())
		
class Aktivasyon(BaseHandler):
    def get(self):
		act_key = cgi.escape(self.request.get('key'))
		qry = User.query(User.activ_key == act_key)
		for usr in qry:
			usr.activ = True
			usr.put()
			self.response.out.write('Hesabınız aktifleştirildi. <a href="/">Anasayfaya</a> dönerek giriş yapabilirsiniz')
			return
		#file = open("activasyon.html");
		#self.response.out.write(file.read())
		self.response.out.write('Geçersiz Kod')
		
class Login(BaseHandler):
    def post(self):
		self.response.out.write(self.request.host_url)
		mail = cgi.escape(self.request.get('mail'))
		password = cgi.escape(self.request.get('password'))
		qry = User.query(User.mail == mail, User.password == password, User.activ == True)
		login = False		
		for usr in qry:
			login = True
			self.response.out.write(usr.key.id())
			self.session['userid'] = usr.key.id()
			self.session['username'] = usr.name
		if login:
			self.redirect("/")
		else :
			file = open("login.html");
			self.response.out.write(file.read())
		
class Dashboard(BaseHandler):
    def get(self):
		file = open("dashboard.html");
		dash = file.read()
		#dash.format(self.session.get('username'),'','')
		self.response.out.write(dash.format(self.session.get('username'),'',''))
		
class Logout(BaseHandler):
    def get(self):
		self.session['userid'] = None
		self.session['username'] = None
		self.redirect('/')
		
class FileUpload(BaseHandler):
	def post(self):		
		fileitem = self.request.POST["filedata"]
		if fileitem.filename:
			fn = os.path.basename(fileitem.filename)
			self.response.out.write(fileitem.file.read())
			message = 'The file "' + fn + '" was uploaded successfully'
		else:
			message = 'No file was uploaded'
			
		self.response.out.write(message)
				
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'my-super-secret-key',
}
app = webapp2.WSGIApplication([
    ('/', MainHandler),
	('/Signup', Signup),
	('/Activasyon', Aktivasyon),
	('/Login', Login),
	('/dashboard', Dashboard),
	('/signup', Signup),
	('/activasyon', Aktivasyon),
	('/login', Login),
	('/dashboard', Dashboard),	
	('/Logout', Logout),	
	('/logout', Logout),
	('/fileupload', FileUpload)
], config=config, debug=True)
