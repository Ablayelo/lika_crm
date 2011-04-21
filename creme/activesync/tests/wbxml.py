# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.test import TestCase

from xml.etree.ElementTree import XML, tostring

from activesync.wbxml.dtd import AirsyncDTD_Reverse, AirsyncDTD_Forward
from activesync.wbxml.codec2 import WBXMLEncoder, WBXMLDecoder

class ActiveSyncWbxmlTestCase(TestCase):
    def setUp(self):
        self.decoder = WBXMLDecoder(AirsyncDTD_Forward)
    
    def test_encoder01(self):
        xml_str1 = '<?xml version="1.0" encoding="UTF-8"?><FolderSync xmlns="FolderHierarchy:"><SyncKey>0</SyncKey></FolderSync>'
        encoder = WBXMLEncoder(AirsyncDTD_Reverse)
        encoded = encoder.encode(xml_str1)
        self.assertEqual(encoded, '\x03\x01j\x00\x00\x07VR\x030\x00\x01\x01')

        self.assertEqual(encoder.get_ns('{FolderHierarchy:}FolderSync'), 'FolderHierarchy:')
        self.assertEqual(encoder.get_ns('FolderHierarchy:FolderSync'),   None)

        self.assertEqual(encoder.get_tag('{FolderHierarchy:}FolderSync', 'FolderHierarchy:'), 'FolderSync')
        self.assertEqual(encoder.get_tag('{FolderHierarchy:}FolderSync', None), '{FolderHierarchy:}FolderSync')


    def test_encoder02(self):
        xml_str2 = """<?xml version="1.0"?><FolderSync xmlns="FolderHierarchy:"><Status xmlns="FolderHierarchy:">1</Status><SyncKey xmlns="FolderHierarchy:">{112ef5a8-47fb-44ca-94e2-d0770e6d7c6b}1</SyncKey><Changes xmlns="FolderHierarchy:"><Count xmlns="FolderHierarchy:">12</Count><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855310d00000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Inbox</DisplayName><Type xmlns="FolderHierarchy:">2</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855310e00000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Outbox</DisplayName><Type xmlns="FolderHierarchy:">6</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855310f00000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Deleted Items</DisplayName><Type xmlns="FolderHierarchy:">4</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311000000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Sent Items</DisplayName><Type xmlns="FolderHierarchy:">5</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311100000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Contacts</DisplayName><Type xmlns="FolderHierarchy:">9</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311200000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Calendar</DisplayName><Type xmlns="FolderHierarchy:">8</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311300000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Drafts</DisplayName><Type xmlns="FolderHierarchy:">3</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311400000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Journal</DisplayName><Type xmlns="FolderHierarchy:">11</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311500000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Notes</DisplayName><Type xmlns="FolderHierarchy:">10</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311600000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Tasks</DisplayName><Type xmlns="FolderHierarchy:">7</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311700000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Junk E-mail</DisplayName><Type xmlns="FolderHierarchy:">12</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311b00000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">RSS Feeds</DisplayName><Type xmlns="FolderHierarchy:">1</Type></Add></Changes></FolderSync>"""
        xml2 = XML(xml_str2)
        wbxml2   = '\x03\x01j\x00\x00\x07VL\x031\x00\x01R\x03{112ef5a8-47fb-44ca-94e2-d0770e6d7c6b}1\x00\x01NW\x0312\x00\x01OH\x032e9ce20a99cc4bc39804d5ee956855310d00000000000000\x00\x01I\x030\x00\x01G\x03Inbox\x00\x01J\x032\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855310e00000000000000\x00\x01I\x030\x00\x01G\x03Outbox\x00\x01J\x036\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855310f00000000000000\x00\x01I\x030\x00\x01G\x03Deleted Items\x00\x01J\x034\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311000000000000000\x00\x01I\x030\x00\x01G\x03Sent Items\x00\x01J\x035\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311100000000000000\x00\x01I\x030\x00\x01G\x03Contacts\x00\x01J\x039\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311200000000000000\x00\x01I\x030\x00\x01G\x03Calendar\x00\x01J\x038\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311300000000000000\x00\x01I\x030\x00\x01G\x03Drafts\x00\x01J\x033\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311400000000000000\x00\x01I\x030\x00\x01G\x03Journal\x00\x01J\x0311\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311500000000000000\x00\x01I\x030\x00\x01G\x03Notes\x00\x01J\x0310\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311600000000000000\x00\x01I\x030\x00\x01G\x03Tasks\x00\x01J\x037\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311700000000000000\x00\x01I\x030\x00\x01G\x03Junk E-mail\x00\x01J\x0312\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311b00000000000000\x00\x01I\x030\x00\x01G\x03RSS Feeds\x00\x01J\x031\x00\x01\x01\x01\x01'
        encoded2 = WBXMLEncoder(AirsyncDTD_Reverse).encode(xml2)
        self.assertEqual(encoded2, wbxml2)


    def test_encoder03(self):
        xml_str3 = """<?xml version="1.0" encoding="utf-8"?><Sync xmlns="AirSync:" xmlns:A1="Contacts:"><Collections><Collection><SyncKey>0</SyncKey><CollectionId>2e9ce20a99cc4bc39804d5ee956855311500000000000000</CollectionId><Supported><A1:JobTitle/><A1:Department/></Supported></Collection></Collections></Sync>"""
        xml3     = XML(xml_str3)
        wbxml3   = '\x03\x01j\x00E\\OK\x030\x00\x01R\x032e9ce20a99cc4bc39804d5ee956855311500000000000000\x00\x01`\x00\x01(\x1a\x01\x01\x01\x01'
        encoded3 = WBXMLEncoder(AirsyncDTD_Reverse).encode(xml3)
        self.assertEqual(encoded3, wbxml3)


    def test_encoder04(self):
        xml_str4 = """<?xml version="1.0" encoding="utf-8"?><Sync xmlns="AirSync:" xmlns:A1="Contacts:"><Collections><Collection><Class>Contacts</Class><SyncKey>0</SyncKey><CollectionId>2e9ce20a99cc4bc39804d5ee956855311b00000000000000</CollectionId><DeletesAsMoves/><GetChanges/></Collection></Collections></Sync>"""
        xml4     = XML(xml_str4)
        wbxml4 = '\x03\x01j\x00E\\OP\x03Contacts\x00\x01K\x030\x00\x01R\x032e9ce20a99cc4bc39804d5ee956855311b00000000000000\x00\x01\x1e\x13\x01\x01\x01'
        encoded4 = WBXMLEncoder(AirsyncDTD_Reverse).encode(xml4)
        self.assertEqual(encoded4, wbxml4)

    def test_encoder_ns_settings(self):
        xml_str = """<?xml version="1.0" encoding="utf-8"?><Settings xmlns="Settings:"><DeviceInformation><Set><Model>CremePhone</Model><IMEI>1234567890</IMEI><FriendlyName>Creme CRM Phone</FriendlyName><OS>Creme/django</OS><OSLanguage>python</OSLanguage><PhoneNumber>0000000000</PhoneNumber><MobileOperator>Hybird</MobileOperator><UserAgent>CremeCRM/1.0</UserAgent></Set></DeviceInformation></Settings>"""
        xml     = XML(xml_str)
        wbxml   = '\x03\x01j\x00\x00\x12EVHW\x03CremePhone\x00\x01X\x031234567890\x00\x01Y\x03Creme CRM Phone\x00\x01Z\x03Creme/django\x00\x01[\x03python\x00\x01\\\x030000000000\x00\x01b\x03Hybird\x00\x01`\x03CremeCRM/1.0\x00\x01\x01\x01\x01'
        encoded = WBXMLEncoder(AirsyncDTD_Reverse).encode(xml)
        self.assertEqual(encoded, wbxml)

    ################ Decoder tests #################
    def test_decoder01(self):
        wbxml_str = '\x03\x01j\x00\x00\x07VR\x030\x00\x01\x01'
        decoded   = self.decoder.decode(wbxml_str)
        xml_str   = '<?xml version="1.0" encoding="UTF-8"?><FolderSync xmlns="FolderHierarchy:"><SyncKey>0</SyncKey></FolderSync>'

        self.assertEqual(tostring(decoded), xml_str)

    def test_decoder02(self):
        wbxml_str = '\x03\x01j\x00\x00\x07VL\x031\x00\x01R\x03{112ef5a8-47fb-44ca-94e2-d0770e6d7c6b}1\x00\x01NW\x0312\x00\x01OH\x032e9ce20a99cc4bc39804d5ee956855310d00000000000000\x00\x01I\x030\x00\x01G\x03Inbox\x00\x01J\x032\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855310e00000000000000\x00\x01I\x030\x00\x01G\x03Outbox\x00\x01J\x036\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855310f00000000000000\x00\x01I\x030\x00\x01G\x03Deleted Items\x00\x01J\x034\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311000000000000000\x00\x01I\x030\x00\x01G\x03Sent Items\x00\x01J\x035\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311100000000000000\x00\x01I\x030\x00\x01G\x03Contacts\x00\x01J\x039\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311200000000000000\x00\x01I\x030\x00\x01G\x03Calendar\x00\x01J\x038\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311300000000000000\x00\x01I\x030\x00\x01G\x03Drafts\x00\x01J\x033\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311400000000000000\x00\x01I\x030\x00\x01G\x03Journal\x00\x01J\x0311\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311500000000000000\x00\x01I\x030\x00\x01G\x03Notes\x00\x01J\x0310\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311600000000000000\x00\x01I\x030\x00\x01G\x03Tasks\x00\x01J\x037\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311700000000000000\x00\x01I\x030\x00\x01G\x03Junk E-mail\x00\x01J\x0312\x00\x01\x01OH\x032e9ce20a99cc4bc39804d5ee956855311b00000000000000\x00\x01I\x030\x00\x01G\x03RSS Feeds\x00\x01J\x031\x00\x01\x01\x01\x01'
        decoded   = self.decoder.decode(wbxml_str)
        xml_str   = """<?xml version="1.0"?><FolderSync xmlns="FolderHierarchy:"><Status xmlns="FolderHierarchy:">1</Status><SyncKey xmlns="FolderHierarchy:">{112ef5a8-47fb-44ca-94e2-d0770e6d7c6b}1</SyncKey><Changes xmlns="FolderHierarchy:"><Count xmlns="FolderHierarchy:">12</Count><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855310d00000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Inbox</DisplayName><Type xmlns="FolderHierarchy:">2</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855310e00000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Outbox</DisplayName><Type xmlns="FolderHierarchy:">6</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855310f00000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Deleted Items</DisplayName><Type xmlns="FolderHierarchy:">4</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311000000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Sent Items</DisplayName><Type xmlns="FolderHierarchy:">5</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311100000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Contacts</DisplayName><Type xmlns="FolderHierarchy:">9</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311200000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Calendar</DisplayName><Type xmlns="FolderHierarchy:">8</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311300000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Drafts</DisplayName><Type xmlns="FolderHierarchy:">3</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311400000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Journal</DisplayName><Type xmlns="FolderHierarchy:">11</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311500000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Notes</DisplayName><Type xmlns="FolderHierarchy:">10</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311600000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Tasks</DisplayName><Type xmlns="FolderHierarchy:">7</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311700000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">Junk E-mail</DisplayName><Type xmlns="FolderHierarchy:">12</Type></Add><Add xmlns="FolderHierarchy:"><ServerId xmlns="FolderHierarchy:">2e9ce20a99cc4bc39804d5ee956855311b00000000000000</ServerId><ParentId xmlns="FolderHierarchy:">0</ParentId><DisplayName xmlns="FolderHierarchy:">RSS Feeds</DisplayName><Type xmlns="FolderHierarchy:">1</Type></Add></Changes></FolderSync>"""

        self.assertEqual(tostring(decoded), xml_str)

    def test_decoder03(self):
        wbxml_str = '\x03\x01j\x00E\\OK\x030\x00\x01R\x032e9ce20a99cc4bc39804d5ee956855311500000000000000\x00\x01`\x00\x01(\x1a\x01\x01\x01\x01'
        decoded   = self.decoder.decode(wbxml_str)
        xml_str   = """<?xml version="1.0" encoding="utf-8"?><Sync xmlns="AirSync:" xmlns:A1="Contacts:"><Collections><Collection><SyncKey>0</SyncKey><CollectionId>2e9ce20a99cc4bc39804d5ee956855311500000000000000</CollectionId><Supported><A1:JobTitle/><A1:Department/></Supported></Collection></Collections></Sync>"""

        self.assertEqual(tostring(decoded), xml_str)

    def test_decoder04(self):
        wbxml_str = '\x03\x01j\x00E\\OP\x03Contacts\x00\x01K\x030\x00\x01R\x032e9ce20a99cc4bc39804d5ee956855311b00000000000000\x00\x01\x1e\x13\x01\x01\x01'
        decoded   = self.decoder.decode(wbxml_str)
        xml_str   = """<?xml version="1.0" encoding="utf-8"?><Sync xmlns="AirSync:" xmlns:A1="Contacts:"><Collections><Collection><Class>Contacts</Class><SyncKey>0</SyncKey><CollectionId>2e9ce20a99cc4bc39804d5ee956855311b00000000000000</CollectionId><DeletesAsMoves/><GetChanges/></Collection></Collections></Sync>"""

        self.assertEqual(tostring(decoded), xml_str)

