import uuid
import cgi
import webapp2
import logging
import os
import md5
import datetime


from google.appengine.api import app_identity
from google.appengine.ext import ndb
from webapp2_extras import sessions
from google.appengine.api import mail

import cloudstorage as gcs

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import cgitb
cgitb.enable()

MAIL_STR = 'Sayın, {0}<br>Hesabınızı Aktifleştirmek için <a href="{1}/Activasyon?key={2}" >Buraya Tıklayınız</a>'
FILETABLE_STR = '<tr><td>{0}</td><td>{1}</td><td>{2}</td><td><a href="/download?id={3}">İndir</a></td></tr>'

my_default_retry_params = gcs.RetryParams(initial_delay=0.2,max_delay=5.0,backoff_factor=2,max_retry_period=15)
										  
gcs.set_default_retry_params(my_default_retry_params)
bucket_name = 'aloboxdeneme'

class User(ndb.Model):
	userid = ndb.IntegerProperty()
	name = ndb.StringProperty()
	mail = ndb.StringProperty()
	password = ndb.StringProperty()
	activ_key = ndb.StringProperty()
	activ = ndb.BooleanProperty()

class FileList(ndb.Model):
	userid = ndb.StringProperty()
	name = ndb.StringProperty()
	size = ndb.IntegerProperty()
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
		passw = x = md5.new(cgi.escape(self.request.get('password'))).hexdigest()
		user = User(name = cgi.escape(self.request.get('firstname')),
					mail = cgi.escape(self.request.get('mail')),
					password = passw,
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
		passw = x = md5.new(cgi.escape(self.request.get('password'))).hexdigest()
		
		qry = User.query(User.mail == mail, User.password == passw, User.activ == True)
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
		tableline = "";
		nofile = True
		qry = FileList.query(FileList.userid == str(self.session['userid']), FileList.deleted == False)
		#self.response.out.write(qry)
		fl_size = 0;
		fl_count = 0;
		for fl in qry:
			fl_count = fl_count + 1
			fl_size = fl_size + fl.size
			tableline = tableline + FILETABLE_STR.format(fl.name, str(fl.size / 1024) + ' KB', fl.loadtime.strftime("%d.%m.%y %H:%M"), fl.c_position)
			nofile = False
		if nofile :
			tableline = '<tr><td colspan="4">Hiç Dosya Bulunamadı</td></tr>'
		#dash.format(self.session.get('username'),'','')
		self.response.out.write(dash.format(self.session.get('username'),fl_count,str(fl_size / 1024) + ' KB', tableline))
		
class Logout(BaseHandler):
    def get(self):
		self.session['userid'] = None
		self.session['username'] = None
		self.redirect('/')
		
class FileUpload(BaseHandler):
	def post(self):
		message  = "";
		fileitem = self.request.POST["filedata"]
		if fileitem.filename:
			fn = os.path.basename(fileitem.filename)
			
			filedata = fileitem.file.read()
			
			cloudfile =  str(uuid.uuid4())
			write_retry_params = gcs.RetryParams(backoff_factor=1.1)
			gcs_file = gcs.open('/' + bucket_name + '/' + cloudfile ,'w',
                        content_type='text/plain',
                        options={'x-goog-meta-foo': 'foo',
                                 'x-goog-meta-bar': 'bar'},
                        retry_params=write_retry_params)
			
			gcs_file.write(filedata)
			gcs_file.close()
			
			filelist = FileList(userid = str(self.session['userid']) ,name = fn, size = len(filedata),	
					loadtime = datetime.datetime.now(), c_position = cloudfile, deleted = False )
			filelist.put();
			self.redirect('/dashboard')
		else:
			message = 'Dosya Yükleme Hatası'
			
		self.response.out.write(message)
			
class Download(BaseHandler):
	def get(self):
		if self.request.GET['id'] :
			qry = FileList.query(FileList.userid == str(self.session['userid']), FileList.deleted == False, FileList.c_position == self.request.GET['id'] )
			for fl in qry :
				filename = '/' + bucket_name + '/' + self.request.GET['id'] 
				gcs_file = gcs.open(filename)
				file = gcs_file.read();
				gcs_file.close()
				self.response.headers['Content-Disposition'] = 'attachment; filename='+ str(fl.name)
				self.response.out.write(file)
				
				self.redirect('/dashboard')
		else :
			self.response.out.write('Dosya Bulunamadı! <a href="/">Anasayfaya</a> dönerek listeyi gözden geçirin')
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'my-super-secret-key',
}
app = webapp2.WSGIApplication([
    ('/', MainHandler),
	('/Signup', Signup),
	('/Activasyon', Aktivasyon),
	('/Login', Login),
	('/Dashboard', Dashboard),
	('/signup', Signup),
	('/activasyon', Aktivasyon),
	('/login', Login),
	('/dashboard', Dashboard),	
	('/Logout', Logout),	
	('/logout', Logout),
	('/fileupload', FileUpload),
	('/download', Download)
], config=config, debug=True)
