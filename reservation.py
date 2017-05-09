#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import uuid
import cgi
import urllib
import wsgiref.handlers
import datetime
from google.appengine.ext import ndb
from google.appengine.api import users
import google.appengine.ext.db
import webapp2
import os
from google.appengine.api import mail
from google.appengine.ext.webapp import template
import jinja2

JINJA_ENVIRONMENT =  jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),extensions=['jinja2.ext.autoescape'],autoescape=True)


class Resource(ndb.Model):

    """Models an individual resource"""

    resourceid = ndb.StringProperty(indexed=True)
    name = ndb.StringProperty(indexed=True)
    tags = ndb.StringProperty(repeated=True)
    starttime = ndb.DateTimeProperty(auto_now_add=False)
    endtime = ndb.DateTimeProperty(auto_now_add=False)
    lastmadereservation = ndb.DateTimeProperty(auto_now_add=False)
    resourceowner = ndb.StringProperty(indexed=True)
    reservedinpastcount = ndb.IntegerProperty()


class Reservation(ndb.Model):
    """Models an individual reservation"""
    reservationid = ndb.StringProperty(indexed=True)
    reservationtime = ndb.DateTimeProperty(auto_now_add=False)
    reservationendtime = ndb.DateTimeProperty(auto_now_add=False)
    reservationduration = ndb.IntegerProperty()
    reservationowner = ndb.StringProperty(indexed=True)
    resourcename = ndb.StringProperty()
    resourceId = ndb.StringProperty(indexed=True)


# def get_key_directly():
#    return ndb.Key('Resource', 'RESOURCE_KEY')


# def get_reservationkey_directly():
#    return ndb.Key('Reservation', 'RESERVATION_KEY')

def getallresourcesbyowner(owner):
    query = Resource.query()
    allresourcesbyowner = query.filter(Resource.resourceowner== owner).order(-Resource.lastmadereservation).fetch()
    return allresourcesbyowner


def getresourcebyval(val):
    query = Resource.query()
    r = query.filter(Resource.resourceid == val).fetch()
    if r:
        return r[0]
    else:
        return None


def getallresourcesbytag(tag):
    allresources = getallresources()
    taggedresources = []
    for r in allresources:
        for t in r.tags:
            if t.strip() == tag.strip():
                taggedresources.append(r)
                continue
    return taggedresources


def getallresources():
    query = Resource.query()
    allresources = query.order(-Resource.lastmadereservation).fetch()
    return allresources


def getallreservationsbyuser(reservationowner):
    query = Reservation.query()
    allreservations = query.filter(Reservation.reservationowner
                                   == reservationowner).order(Reservation.reservationtime).fetch()
    newreservations = []
    for r in allreservations:
        current_date = datetime.datetime.now() \
            - datetime.timedelta(hours=4)
        end_date = r.reservationtime \
            + datetime.timedelta(minutes=int(r.reservationduration))
        if current_date <= end_date:
            newreservations.append(r)
    return newreservations


class MainPage(webapp2.RequestHandler):

    def get(self):

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            resources = getallresources()
            ownerresources = getallresourcesbyowner(users.get_current_user().email())
            reservations = getallreservationsbyuser(users.get_current_user().email())
            template_values = {
                'resources': resources,
                'ownerresources': ownerresources,
                'reservations': reservations,
                'url': url,
                'url_linktext': url_linktext,
                'user': users.get_current_user().email(),
                }
            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.out.write(template.render(template_values))
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            self.redirect(url)


class AddResource(webapp2.RequestHandler):

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('addResource.html')
        template_values = {}
        self.response.write(template.render(template_values))

    def post(self):
        resourcename = self.request.get('name')
        resourcetags = self.request.get('tags').split(',')
        resourcestarttime = self.request.get('starttime')
        resourceendtime = self.request.get('endtime')
        starthour=int(resourcestarttime.strip().split(':')[0])
        startminute=int(resourcestarttime.strip().split(':')[1])
        endhour=int(resourceendtime.strip().split(':')[0])
        endminute=int(resourceendtime.strip().split(':')[1])
        currentdatetime=datetime.datetime.now() - datetime.timedelta(hours=4)
        availabilitystarttime = datetime.datetime.combine(currentdatetime.date(),datetime.time(starthour, startminute))
        availabilityendtime = datetime.datetime.combine(currentdatetime.date(),datetime.time(endhour, endminute))
        r = Resource()
        # r = Resource(parent=get_key_directly())
        r.name = resourcename
        r.resourceowner = str(users.get_current_user().email())
        r.tags = resourcetags
        r.starttime = availabilitystarttime
        r.endtime = availabilityendtime
        r.reservedinpastcount=0
        r.count = 0
        uid = uuid.uuid1()
        uid_str = uid.urn
        r.resourceid = uid_str[9:]
        r.put()
        self.redirect('/')


class SearchResource(webapp2.RequestHandler):

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('searchresource.html')
        template_values = {}
        self.response.write(template.render(template_values))

    def post(self):

        # template = JINJA_ENVIRONMENT.get_template('addResource.html')
        flag=0
        if self.request.get('name'):
         resourcename = self.request.get('name')
         flag=1
         
        if self.request.get('duration') and self.request.get('starttime'):
           resourceduration = int(self.request.get('duration'))
           resourcestarttime = self.request.get('starttime')
           flag=2
        resourcelist=[]    
        error = ''
        query = Resource.query()
        if flag==1:
            resourcelist = query.filter(Resource.name
                    == resourcename).order(-Resource.lastmadereservation).fetch()
        elif flag==2:
            allresources=getallresources()
            starthour=int(resourcestarttime.strip().split(':')[0])
            startminute=int(resourcestarttime.strip().split(':')[1])
            availabilitydate = datetime.datetime.now()- datetime.timedelta(hours=4)
            availabilitystarttime = datetime.datetime.combine(availabilitydate.date(),datetime.time(starthour, startminute))
            availabilityendtime = availabilitystarttime + datetime.timedelta(minutes=resourceduration)
            #logging.info('availability start time')
            #logging.info(availabilitystarttime.time())
            #logging.info('availability end time')
            #logging.info(availabilityendtime)

            for r in query:
                #logging.info('resource end time is')
                #logging.info(r.endtime)
                #logging.info('resource start time is')
                #logging.info(r.starttime)
                if (availabilitystarttime.time()>=r.starttime.time()  and availabilityendtime.time()<=r.endtime.time() ):
                    resourcelist.append(r) 
        else:
            error = 'You have to provide either name or both availability start time and duration'

        template = JINJA_ENVIRONMENT.get_template('searchresource.html')
        template_values = {'uierror': error,'resourcelist': resourcelist}
        self.response.write(template.render(template_values))


class Addreservation(webapp2.RequestHandler):

    def get(self):
        val = str(self.request.get('rval'))
        template = JINJA_ENVIRONMENT.get_template('addReservation.html')
        r = getresourcebyval(val)
        template_values = {'val': val,
                           'user': str(users.get_current_user().email()),
                           'resourceuser': r.resourceowner}
        self.response.write(template.render(template_values))

    def post(self):
        flag = 0
        resourcename = str(self.request.get('val'))
        reservationtime = self.request.get('starttime')
        reservationduration = int(self.request.get('duration'))
        reservationdate = self.request.get('reservationdate')
        reservationowner = str(users.get_current_user().email())
        logging.info("Time now is")
        logging.info(reservationtime)
        starthour = int(reservationtime.strip().split(':')[0])
        startminute=int(reservationtime.strip().split(':')[1])



        reservationdate = datetime.datetime.strptime(reservationdate,'%Y-%m-%d').date()
        availabilitystarttime = datetime.datetime.combine(reservationdate,datetime.time(starthour, startminute))
        availabilityendtime = availabilitystarttime + datetime.timedelta(minutes=reservationduration)
        error = ''

        currentdatetime=datetime.datetime.now() - datetime.timedelta(hours=4)
        r = getresourcebyval(resourcename)
        query = Reservation.query()
        allreservations = query.filter(Reservation.reservationowner==reservationowner).fetch()
        ###########Checking for Overlapping of Reservations for the same user###################
        for a in allreservations:
            logging.info("input availablility end time")
            logging.info(availabilityendtime)
            logging.info("input availablility start time")
            logging.info(availabilitystarttime)
            logging.info("reservation end time")
            logging.info(a.reservationendtime)
            logging.info("reservation start time")
            logging.info(a.reservationtime)
            #delta = min(availabilityendtime,a.reservationendtime)-max(availabilitystarttime,a.reservationtime)
            #if delta.seconds < 0:
            #logging.info(delta.seconds)
            if (a.reservationtime >=availabilitystarttime and a.reservationtime <=availabilityendtime and a.reservationendtime >=availabilitystarttime  and a.reservationendtime <=availabilityendtime) or (availabilitystarttime >= a.reservationtime   and availabilitystarttime <=a.reservationendtime) or (availabilityendtime >=a.reservationtime  and availabilityendtime <=a.reservationendtime):
                error='You cannot create a reservation for the following period as it is overlapping with an existing reservation.' 
                break 
        ###########Checking for Resource Availability###################
 
        if r is None:
            error = 'The resource is not present'
        elif r.starttime.time() > availabilitystarttime.time()  or r.endtime.time() < availabilityendtime.time():
            error = 'The resource ' + r.name + ' cannot be reserved for the given duration as it is outside the available time range of resource.'
        elif reservationdate < currentdatetime.date():
            error = 'The reservation date cannot be a past day'
        if error:
            template = JINJA_ENVIRONMENT.get_template('addReservation.html')
            template_values = {
                'val': resourcename,
                'uierror': error,
                'user': str(users.get_current_user().email()),
                'resourceuser': r.resourceowner,
                }
            self.response.write(template.render(template_values))
        else:

            # res = Reservation(parent=get_reservationkey_directly())
            res = Reservation()
            res.reservationtime = availabilitystarttime
            res.reservationowner = reservationowner
            res.reservationduration = reservationduration
            res.reservationendtime=res.reservationtime + datetime.timedelta(minutes=res.reservationduration) 
            res.reservationid = resourcename
            res.resourcename = r.name
            res.resourceId = r.resourceid
            r.lastmadereservation = availabilitystarttime
            r.reservedinpastcount = r.reservedinpastcount + 1
            r.put()
            uid = uuid.uuid1()
            uid_str = uid.urn
            res.reservationid = uid_str[9:]
            res.put()
            message = mail.EmailMessage()
            message.sender = 'vr840@nyu.edu'
            message.to = [users.get_current_user().email()]
            message.subject = 'Reservation Created for Resource ' \
                + r.name
            message.body = \
                """Dear Sir/Madam,Your reservation has been created for the resource """ \
                + r.name + """The reservation is created on """ \
                + str(res.reservationtime) + """ for a duration """ \
                + str(reservationduration) + """ minutes.""" \
                + """Please let us know if you have any questions.The Reservation System Team"""
            message.check_initialized()
            message.send()
            self.redirect('/')


class EditResource(webapp2.RequestHandler):

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('editresource.html')
        val = str(self.request.get('rval'))
        r = getresourcebyval(val)

        template_values = {
            'val': val,
            'resourcename': r.name,
            'resourcestarttime': r.starttime.time(),
            'resourceendtime': r.endtime.time(),
            'resourcetags': ', '.join(r.tags),
            }

        self.response.write(template.render(template_values))

    def post(self):
        val = str(self.request.get('val'))
        resourcename = self.request.get('name')
        resourcetags = self.request.get('tags').strip().split(',')
        resourcestarttime = self.request.get('starttime')
        resourceendtime = self.request.get('endtime')
        #logging.info("start time is")
        #logging.info(resourcestarttime)

        starthour = int(resourcestarttime.strip().split(':')[0])
        startminute=int(resourcestarttime.strip().split(':')[1])  
        endhour=int(resourceendtime.strip().split(':')[0])
        endminute=int(resourceendtime.strip().split(':')[1])
        currentdatetime=datetime.datetime.now() - datetime.timedelta(hours=4)

        availabilitystarttime = datetime.datetime.combine(currentdatetime.date(),datetime.time(starthour, startminute))
        availabilityendtime =  datetime.datetime.combine(currentdatetime.date(),datetime.time(endhour, endminute))
        # r = Resource(parent=resource_key())
        val = str(self.request.get('val'))
        r = getresourcebyval(val)
        r.name = resourcename
        r.tags = resourcetags
        r.starttime = availabilitystarttime
        r.endtime = availabilityendtime
        r.count = 0
        r.put()
        self.redirect('/')


class generateRSS(webapp2.RequestHandler):

    def get(self):
        val = str(self.request.get('rval'))
        res = getresourcebyval(val)
        query = Reservation.query()
        allreservations = query.filter(Reservation.resourceId
                == res.resourceid).order(Reservation.reservationtime).fetch()
        resourcename = res.name
        template = JINJA_ENVIRONMENT.get_template('generateRSS.html')
        template_values = {'val': val, 'resourcename': resourcename,
                           'allreservations': allreservations}
        self.response.write(template.render(template_values))


class UpcomingReservations(webapp2.RequestHandler):

    def get(self):
        val = str(self.request.get('rval'))
        res = getresourcebyval(val)
        query = Reservation.query()
        allreservations = query.filter(Reservation.resourceId == res.resourceid).order(Reservation.reservationtime).fetch()
        newreservations = []
        # Coordinated Universal Time is 4 hours ahead of New York, NY
        currentdatetime=datetime.datetime.now() - datetime.timedelta(hours=4)
        for r in allreservations:
            #end_date = r.reservationtime + datetime.timedelta(minutes=int(r.reservationduration))
            if currentdatetime <= r.reservationendtime:
                newreservations.append(r)
        template_values = {'UpcomingReservations': newreservations,
                           'user': str(users.get_current_user().email())}
        template = JINJA_ENVIRONMENT.get_template('upcomingreservation.html')
        self.response.write(template.render(template_values))


class Deletereservation(webapp2.RequestHandler):

    def get(self):
        val = str(self.request.get('rval'))
        reservationid = str(val)
        
        reservations = getallreservationsbyuser(str(users.get_current_user().email()))
        for r in reservations:
            if r.reservationid == reservationid:
                resource=getresourcebyval(r.resourceId)
                resource.reservedinpastcount=resource.reservedinpastcount-1
                resource.put()
                r.key.delete()
                break
        self.redirect('/')


class Resourceinfo(webapp2.RequestHandler):

    def get(self):
        val = str(self.request.get('rval'))
        ownerresources = getallresourcesbyowner(val)
        ownerreservations = getallreservationsbyuser(val)
        template_values = {'ownerresources': ownerresources,
                           'reservations': ownerreservations,
                           'user': users.get_current_user().email()}
        template = JINJA_ENVIRONMENT.get_template('resourceinfo.html')
        self.response.write(template.render(template_values))


class Resourcetag(webapp2.RequestHandler):

    def get(self):
        taggedresources = getallresourcesbytag(self.request.get('tagval'
                ))
        template_values = {'taggedresources': taggedresources,
                           'tagval': self.request.get('tagval'),
                           'user': str(users.get_current_user().email())}
        template = JINJA_ENVIRONMENT.get_template('resourcetag.html')
        self.response.write(template.render(template_values))


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/addResource', AddResource),
    ('/resourcetag', Resourcetag),
    ('/addreservation', Addreservation),
    ('/deletereservation', Deletereservation),
    ('/resourceinfo', Resourceinfo),
    ('/upcomingreservation', UpcomingReservations),
    ('/editresource', EditResource),
    ('/generateRSS', generateRSS),
    ('/searchresource', SearchResource),
    ], debug=True)


            