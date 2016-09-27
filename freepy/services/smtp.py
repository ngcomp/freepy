# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# Thomas Quintana <quintana.thomas@gmail.com>

from freepy.lib.application import Actor
from freepy.lib.server import RegisterActorCommand, RouteMessageCommand, \
                       ServerDestroyEvent, ServerInitEvent

from zope.interface import implements

from twisted.internet import protocol, reactor, defer
from twisted.mail import smtp
from email.header import Header

import logging
from freepy import settings


class SmtpDispatcher(Actor):
  def __init__(self, *args, **kwargs):
    super(SmtpDispatcher, self).__init__(*args, **kwargs)
    self.__logger__ = logging.getLogger('services.smtp.SmtpDispatcher')

  def _dispatch(self, message):
    self.__server__.tell(RouteMessageCommand(message, self._target))
    return

  def _initialize(self, message):
    self.__server__ = message.server()
    for item in message.meta():
      if item and item.has_key('smtp'):
        smtp = item.get('smtp')
        self._whitelist = smtp.get('whitelist').get('ips')
        self._allow_all = smtp.get('whitelist').get('allow_all')


        rule = smtp.get('rule')
        try:
          if rule is not None and len(rule) > 0:
            singleton = rule.get('singleton')
            self._target = rule.get('target')
            self.__server__.tell(RegisterActorCommand(self._target, singleton))
            self.__logger__.info("Registered {}".format(self._target))
        except Exception as e:
          self.__logger__.exception(e)

    self._start()

  def _start(self):
    reactor.listenTCP(settings.smtp.get('port'), SmtpFactory(self))

  def receive(self, message):
    if isinstance(message, SmtpReceiveEvent):
      self._dispatch(message)
    elif isinstance(message, ServerInitEvent):
      self._initialize(message)


class SmtpMessage(object):
  implements(smtp.IMessage)

  def __init__(self, dispatcher):
    self.__logger__ = logging.getLogger('services.smtp.SmtpDispatcher')
    self._dispatcher = dispatcher
    self.lines = []
    self.received = None
    self.headers = None
    self.body = None

  def lineReceived(self, line):
    self.lines.append(line)

  def eomReceived(self):
    self.format_data()
    event = SmtpReceiveEvent(self.received, self.headers, self.body)
    self._dispatcher._dispatch(event)
    return defer.succeed(None)

  def connectionLost(self):
    self.__logger__.error("Connection lost")

  def format_data(self):
    self.__logger__.debug("unformatted smtp message: ")
    self.__logger__.debug(self.lines)

    self.received = self.lines[0]
    header_lines = []
    body_lines = []
    end_headers = False
    for line in self.lines[1:]:
      if line == "" and not end_headers:
        end_headers = True
      elif not end_headers:
        header_lines.append(line)
      else:
        body_lines.append(line)

    self.headers = {}
    for line in header_lines:
      try:
        header_content = line.split(": ")
        header_name = header_content[0]
        header_value = header_content[1]
        self.headers[header_name] = header_value
      except Exception as e:
        self.__logger__.error("Faulty header: {}".format(line))
        self.__logger__.exception(e)

    self.body = "\n".join(body_lines)


class SmtpMessageDelivery(object):
  implements(smtp.IMessageDelivery)

  def __init__(self, dispatcher):
    self._dispatcher = dispatcher
    self._whitelist = dispatcher._whitelist
    self._allow_all = dispatcher._allow_all
    self.__logger__ = logging.getLogger('services.smtp.SmtpDispatcher')

  def receivedHeader(self, helo, origin, recipients):
    myHostname, clientIP = helo
    headerValue = 'by {} from {} with SMTP ; {}'.format(myHostname, clientIP, smtp.rfc822date( ))
    return 'Received: {}'.format(Header(headerValue))

  def validateTo(self, user):
    # whitelist here. if not on whitelist,
    # raise smtp.SMTPBadRcpt(user)
    return lambda: SmtpMessage(self._dispatcher)

  def validateFrom(self, helo, originAddress):
    myHostname, clientIP = helo
    if self._allow_all or str(clientIP) in self._whitelist:
      return originAddress

    self.__logger__.error('Sender not whitelisted')
    self.__logger__.error('offending IP: '+str(clientIP))
    raise smtp.SMTPBadSender(originAddress)


class SmtpFactory(protocol.ServerFactory):
  def __init__(self, dispatcher):
    self.__logger__ = logging.getLogger('services.smtp.SmtpDispatcher')
    self.__dispatcher__ = dispatcher

  def buildProtocol(self, addr):
    delivery = SmtpMessageDelivery(self.__dispatcher__)
    smtpProtocol = smtp.SMTP(delivery)
    smtpProtocol.factory = self

    return smtpProtocol


class SmtpReceiveEvent(object):
  def __init__(self, received, headers, body):
    self._body = body
    self._headers = headers
    self._received = received

  def body(self):
    return self._body

  def headers(self):
    return self._headers

  def received(self):
    return self._received
