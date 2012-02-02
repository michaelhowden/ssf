# -*- coding: utf-8 -*-
""" Sahana Eden Survey Tool

    ADAT - Assessment Data Analysis Tool

    @author: Graeme Foster <graeme at acm dot org>

    For more details see the blueprint at:
    http://eden.sahanafoundation.org/wiki/BluePrint/SurveyTool/ADAT

    @copyright: 2009-2011 (c) Sahana Software Foundation
    @license: MIT

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use,
    copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following
    conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.
"""

__all__ = ["S3TemplateModel",
           "S3QuestionModel",
           "S3FormatterModel",
           "S3SeriesModel",
           "S3CompleteModel",
           "S3TranslateModel",
           "survey_template_represent",
           "survey_series_represent",
           "survey_answer_list_represent",
           "survey_template_rheader",
           "survey_series_rheader",
           "survey_getAllSectionsForTemplate",
           "survey_getAllQuestionsForTemplate",
           "survey_buildQuestionnaireFromTemplate",
           "survey_buildQuestionnaireFromSeries",
           "survey_getTemplate",
           "survey_getTemplateFromSeries",
           "survey_getAllTemplates",
           "survey_getAllWidgetsForTemplate",
           "survey_getAllSectionsForSeries",
           "survey_getAllSectionsForTemplate",
           "survey_getQuestionFromCode",
           "survey_getAllQuestionsForTemplate",
           "survey_getAllQuestionsForSeries",
           "survey_getAllQuestionsForComplete",
           "survey_save_answers_for_series",
           "survey_updateMetaData",
           "survey_getAllAnswersForQuestionInSeries",
           "survey_getQstnLayoutRules",
           "survey_getSeries",
           "survey_getSeriesName",
           "survey_getAllSeries",
           "survey_getTranslation",
           "survey_getAllTranslationsForTemplate",
           "survey_getAllTranslationsForSeries",
           "survey_build_template_summary",
           "survey_build_series_summary",
           "survey_serieslist_dataTable_post",
           "survey_answerlist_dataTable_pre",
           "survey_answerlist_dataTable_post",
           "survey_json2py",
           "survey_json2list",
          ]

from gluon import *
from gluon.storage import Storage
from ..s3 import *

import sys
sys.path.append("applications/%s/modules/s3" % current.request.application)
from s3survey import survey_question_type, \
                     survey_analysis_type, \
                     _debug

def json2py(jsonstr):
    """
        Utility function to convert a string in json to a pythin structure
    """
    import gluon.contrib.simplejson as json
    from xml.sax.saxutils import unescape

    try:
        rawjson = unescape(jsonstr, {"u'": '"'})
        rawjson = unescape(rawjson, {"'": '"'})
        pythonStructure = json.loads(rawjson)
    except:
        _debug("ERROR: attempting to convert %s using modules/eden/survey/json2py.py" % (jsonstr))
        return jsonstr
    else:
        return pythonStructure
survey_json2py = json2py

def json2list(jsonstr):
    """
        Used to modify a json string to a python list.
    """
    if jsonstr == "":
        valueList = []
    else:
        if jsonstr[0] == "[":
            valueList = json2py(jsonstr)
        else:
            valueList = jsonstr.split(",")
        if not isinstance(valueList, list):
            valueList = [valueList]
    return valueList
survey_json2list = json2list

class S3TemplateModel(S3Model):
    """
        Template model

        The template model is a container for the question model
    """
    names = ["survey_template",
             "survey_template_id",
             "survey_section"
            ]

    def model(self):

        db = current.db
        T = current.T
        s3 = current.response.s3

        template_status = {
                            1: T("Pending"),
                            2: T("Active"),
                            3: T("Closed"),
                            4: T("Master")
                          }

        # The location hierarchy strings are added here (rather than using
        # the system settings) because they will be dynamically
        # translated when the spreadsheet is printed
        hierarchy_elements = {
                              "L0":"Country",
                              "L1":"State",
                              "L2":"City",
                              "L3":"Town",
                              "L4":"Neighborhood",
                              "Lat":"Latitude",
                              "Lon":"Longitude",
                             }

        """
            The survey_template table

            The template is the root table and acts as a container for
            the questions that will be used in a survey.
        """
        tablename = "survey_template"
        table = self.define_table(tablename,
                                   Field("name",
                                         "string",
                                         label = T("Template Name"),
                                         default="",
                                         length=120,
                                         notnull=True,
                                         unique=True,
                                         ),
                                   Field("description", "text", default="", length=500),
                                   Field("status",
                                         "integer",
                                         requires = IS_IN_SET(template_status,
                                                              zero=None),
                                         default=1,
                                         represent = lambda index: template_status[index],
                                         readable=True,
                                         writable=False),
                                   # Standard questions which may belong to all template
                                   # competion_qstn: who completed the assessment
                                   # date_qstn: when it was completed (date)
                                   # time_qstn: when it was completed (time)
                                   # location_detail: json of the location question
                                   #                  May consist of any of the following:
                                   #                  L0, L1, L2, L3, L4, Lat, Lon
                                   Field("competion_qstn",
                                         "string",
                                         length=200,
                                        ),
                                   Field("date_qstn",
                                         "string",
                                         length=200,
                                        ),
                                   Field("time_qstn",
                                         "string",
                                         length=200,
                                        ),
                                   Field("location_detail",
                                         "string",
                                         length=200,
                                        ),
                                   # The priority question is the default question used in the map
                                   # to determine to priority need of each point.
                                   # The data is stored as the question code.
                                   Field("priority_qstn",
                                         "string",
                                         length=16,
                                         label = T("Default map question"),
                                        ),
                                   *s3.meta_fields())

        # CRUD Strings
        s3.crud_strings[tablename] = Storage(
            title_create = T("Add Assessment Template"),
            title_display = T("Assessment Template Details"),
            title_list = T("List of Assessment Templates"),
            title_analysis_summary = T("Template Summary"),
            title_update = T("Edit Assessment Template"),
            title_question_details = T("Details of each question in the Template"),
            subtitle_create = T("Add a new Assessment Template"),
            subtitle_list = T("Assessment Templates"),
            subtitle_analysis_summary = T("Summary by Question Type - (The fewer text questions the better the analysis can be)"),
            label_list_button = T("List all Assessment Templates"),
            label_create_button = T("Add a new Assessment Template"),
            label_delete_button = T("Delete this Assessment Template"),
            msg_record_created = T("Assessment Template added"),
            msg_record_modified = T("Assessment Template updated"),
            msg_record_deleted = T("Assessment Template deleted"),
            msg_list_empty = T("No Assessment Templates currently registered"))



        template_id = S3ReusableField("template_id",
                                      db.survey_template,
                                      sortby="name",
                                      label=T("Template"),
                                      requires = IS_ONE_OF(db,
                                                           "survey_template.id",
                                                           self.survey_template_represent,
                                                           ),
                                      represent = self.survey_template_represent,
                                      ondelete = "RESTRICT")
        self.add_component(table, survey_template="template_id")
        # components
        self.add_component("survey_translate",
                           survey_template = "template_id"
                          )
        self.configure(tablename,
                        onvalidation = self.template_onvalidate,
                        onaccept = self.template_onaccept,
                        deduplicate = self.survey_template_duplicate,
                        )

        """
            The survey_sections table

            The questions can be grouped into sections this provides
            the description of the section and
            the position of the section within the template
        """
        tablename = "survey_section"
        table = self.define_table(tablename,
                                 Field("name",
                                       "string",
                                       default="",
                                       length=120,
                                       notnull=True,
                                       ),
                                 Field("description",
                                       "text",
                                       default="",
                                       length=500),
                                 Field("posn",
                                       "integer",
                                       ),
                                 Field("cloned_section_id",
                                       "integer",
                                       readable=False,
                                       writable=False,
                                       ),
                                 template_id(),
                                 *s3.meta_fields())

        # CRUD Strings
        s3.crud_strings[tablename] = Storage(
            title_create = T("Add Template Section"),
            title_display = T("Template Section Details"),
            title_list = T("List of Template Sections"),
            title_update = T("Edit Template Section"),
            subtitle_create = T("Add a new Template Section"),
            subtitle_list = T("Template Sections"),
            label_list_button = T("List all Template Sections"),
            label_create_button = T("Add a new Template Section"),
            label_delete_button = T("Delete this Template Section"),
            msg_record_created = T("Template Section added"),
            msg_record_modified = T("Template Section updated"),
            msg_record_deleted = T("Template Section deleted"),
            msg_list_empty = T("No Template Sections currently registered"))

        self.configure(tablename, orderby = tablename+".posn",
                       deduplicate=self.survey_section_duplicate
                      )


        # Return names to response.s3
        return Storage(
            survey_template_id = template_id,
            survey_template_status = template_status,
            survey_hierarchy_elements = hierarchy_elements,
        )

    # ---------------------------------------------------------------------
    # Static so that calling it doesn't require loading the models
    @staticmethod
    def template_onvalidate(form):
        """
            It is not valid to re-import a template that already has a
            status of Active or higher
        """
        template_id = form.vars.id
        template = getTemplate(template_id)
        if template != None and template.status > 1:
            return False
        return True

    @staticmethod
    def addQuestion(template_id, name, code, notes, type, posn, metadata={}):
        db = current.db
        s3db = current.s3db

        # Add the question to the database if it's not already there
        qstntable = s3db.survey_question
        query = (qstntable.name == name) & \
                (qstntable.code == code)
        record = db(query).select(qstntable.id, limitby=(0, 1)).first()
        if record:
            qstn_id = record.id
        else:
            qstn_id = qstntable.insert(name = name,
                                       code = code,
                                       notes = notes,
                                       type = type
                                      )
            qstn_metadata_table = s3db.survey_question_metadata
            for (descriptor, value) in metadata.items():
                qstn_metadata_table.insert(question_id = qstn_id,
                                           descriptor = descriptor,
                                           value = value 
                                          )
        # Add these questions to the section: "Background Information"
        sectable = s3db.survey_section
        section_name = "Background Information"
        query = (sectable.name == section_name) & \
                (sectable.template_id == template_id)
        record = db(query).select(sectable.id, limitby=(0, 1)).first()
        if record:
            section_id = record.id
        else:
            section_id = sectable.insert(name = section_name,
                                         template_id = template_id,
                                         posn = 0 # special section with no position
                                        )
        # Add the question to the list of questions in the template
        qstn_list_table = s3db.survey_question_list
        query = (qstn_list_table.question_id == qstn_id) & \
                (qstn_list_table.template_id == template_id)
        record = db(query).select(qstntable.id, limitby=(0, 1)).first()
        if not record:
            qstn_list_table.insert(question_id = qstn_id,
                                   template_id = template_id,
                                   section_id = section_id,
                                   posn = posn
                                  )

    @staticmethod
    def template_onaccept(form):
        """
            All of the standard questions will now be generated
            competion_qstn: who completed the assessment
            date_qstn: when it was completed (date)
            time_qstn: when it was completed (time)
            location_detail: json of the location question
                             May consist of any of the following:
                             L0, L1, L2, L3, L4, Lat, Lon
                             for json entry a question will be generated
            The code for each question will start with "STD-" followed by
            the type of question.
        """
        if form.vars.id:
            template_id = form.vars.id
        else:
            return
        addQuestion = S3TemplateModel.addQuestion
        if form.vars.competion_qstn != None:
            name = form.vars.competion_qstn
            code = "STD-WHO"
            notes = "Who completed the assessment"
            type = "String"
            posn = -10 # negative used to force these question to appear first
            addQuestion(template_id, name, code, notes, type, posn)
        if form.vars.date_qstn != None:
            name = form.vars.date_qstn
            code = "STD-DATE"
            notes = "Date the assessment was completed"
            type = "Date"
            posn += 1
            addQuestion(template_id, name, code, notes, type, posn)
        if form.vars.time_qstn != None:
            name = form.vars.time_qstn
            code = "STD-TIME"
            notes = "Time the assessment was completed"
            type = "String"
            posn += 1
            addQuestion(template_id, name, code, notes, type, posn)
        if form.vars.location_detail != None:
            s3 = current.response.s3
            locationList = json2py(form.vars.location_detail)
            if len(locationList) > 0:
                name = "The location P-code"
                code = "STD-P-Code"
                type = "String"
                posn += 1
                addQuestion(template_id, name, code, None, type, posn)
            for loc in locationList:
                if loc in s3.survey_hierarchy_elements:
                    name = s3.survey_hierarchy_elements[loc]
                else:
                    continue
                code = "STD-%s" % loc
                if loc == "Lat" or loc == "Lon":
                    type = "Numeric"
                    metadata = {"Format": "nnn.nnnnnn"}
                else:
                    type = "Location"
                    metadata = {}
                posn += 1
                addQuestion(template_id, name, code, "", type, posn, metadata)

    @staticmethod
    def survey_template_duplicate(job):
        """
          Rules for finding a duplicate:
           - Look for a record with the same name, ignoring case
        """
        if job.tablename == "survey_template":
            table = job.table
            name = "name" in job.data and job.data.name
            query =  table.name.lower().like('%%%s%%' % name.lower())
            return duplicator(job, query)


    @staticmethod
    def survey_section_duplicate(job):
        """
          Rules for finding a duplicate:
           - Look for a record with the same name
           - the same template
           - and the same position within the template
           - however if their is a record with position of zero then that record should be updated
        """
        db = current.db

        if job.tablename == "survey_section":
            table = job.table
            name = "name" in job.data and job.data.name
            template = "template_id" in job.data and job.data.template_id
            query = (table.name == name) & \
                    (table.template_id == template)
            posn = "posn" in job.data and job.data.posn
            record = db(query & (table.posn == 0)).select(table.posn, limitby=(0, 1)).first()
            if not record:
                query = query & (table.posn == posn)
            return duplicator(job, query)


# =============================================================================

def survey_template_represent(id):
    """
        Display the template name rather than the id
    """
    s3db = current.s3db
    table = s3db.survey_template

    db = current.db
    query = (table.id == id)
    record = db(query).select(table.name,limitby=(0, 1)).first()
    if record:
        return record.name
    else:
        return None

def survey_template_rheader(r, tabs=[]):
    """
        The template rheader
    """
    s3db = current.s3db
    db = current.db
    T = current.T
    auth = current.auth
    request = current.request
    s3 = current.response.s3

    if r.representation == "html":

        tablename, record = s3_rheader_resource(r)
        if tablename == "survey_template" and record:

            # Tabs
            tabs = [(T("Basic Details"), "read"),
                    (T("Question Details"),"templateRead/"),
                    (T("Question Summary"),"templateSummary/"),
#                            (T("Sections"), "section"),
                   ]
            if auth.s3_has_permission("create", "survey_translate"):
                tabs.append((T("Translate"),"translate"))

            rheader_tabs = s3_rheader_tabs(r, tabs)

            sectionTable = s3db["survey_section"]
            qlistTable = s3db["survey_question_list"]
            if "vars" in request and "viewing" in request.vars:
                dummy, template_id = request.vars.viewing.split(".")
            else:
                template_id = r.id

            query = (qlistTable.template_id == template_id) & \
                    (qlistTable.section_id == sectionTable.id)
            rows = db(query).select(sectionTable.id,
                                    sectionTable.name,
                                    orderby = qlistTable.posn)
            tsection = TABLE(_class="survey-section-list")
            lblSection = SPAN(T("Sections that are part of this template"),
                              _style="font-weight:bold;")
            if (rows.__len__() == 0):
                rsection = SPAN(T("As of yet, no sections have been added to this template."))
            else:
                rsection = TR()
                count = 0
                lastSection = ""
                for section in rows:
                    if section.name == lastSection:
                        continue
                    rsection.append(TD(section.name))
#                            # Comment out the following until templates can be built online
#                            rsection.append(TD(A(section.name,
#                                                 _href=URL(c="survey",
#                                                           f="section",
#                                                           args="%s" % section.id))))
                    lastSection = section.name
                    count += 1
                    if count % 4 == 0:
                        tsection.append(rsection)
                        rsection=TR()
            tsection.append(rsection)


            rheader = DIV(TABLE(
                          TR(
                             TH("%s: " % T("Name")),
                             record.name,
                             TH("%s: " % T("Status")),
                             s3.survey_template_status[record.status],
                             ),
                              ),
                          lblSection,
                          tsection,
                          rheader_tabs)
            return rheader
    return None

def survey_getTemplate(template_id):
    """
        Return the template data from the template id passed in
    """
    s3db = current.s3db
    db = current.db

    table = s3db.survey_template
    query = (table.id == template_id)
    return db(query).select(limitby=(0, 1)).first()

def survey_getTemplateFromSeries(series_id):
    """
        Return the template data from the series_id passed in
    """
    series = survey_getSeries(series_id)
    if series != None:
        template_id = series.template_id
        return survey_getTemplate(template_id)
    else:
        return None

def survey_getAllTemplates():
    """
        function to return all the templates on the database
    """
    s3db = current.s3db
    db = current.db

    table = s3db.survey_template
    row = db(table).select()
    return row

def survey_getAllWidgetsForTemplate(template_id):
    """
        function to return the widgets for each question for the given
        template. The widgets are returned in a dict with the key being
        the question code.
    """
    s3db = current.s3db
    db = current.db

    q_ltable = s3db.survey_question_list
    qsntable = s3db.survey_question
    query = db((q_ltable.template_id == template_id) & \
               (q_ltable.question_id == qsntable.id)
              )
    rows = query.select(qsntable.id,
                        qsntable.code,
                        qsntable.type,
                        q_ltable.posn,
                        )
    widgets = {}
    for row in rows:
        qstnType = row.survey_question.type
        qstn_id = row.survey_question.id
        qstn_code = row.survey_question.code
        qstn_posn = row.survey_question_list.posn
        widgetObj = survey_question_type[qstnType](qstn_id)
        widgets[qstn_code] = widgetObj
        widgetObj.question["posn"] = qstn_posn
        question = {}
    return widgets


def survey_getAllSectionsForSeries(series_id):
    """
        function to return the list of sections for the given series
        The sections are returned in the order of their position in the
        template.

        The data on each section is held in a dict and is as follows:
        section_id, name, template_id, and posn
    """
    row = survey_getSeries(series_id)
    template_id = row.template_id
    return survey_getAllSectionsForTemplate(template_id)


def survey_buildQuestionnaireFromTemplate(template_id):
    """
        build a form displaying all the questions for a given template_id
    """
    s3 = current.response.s3
    questions = survey_getAllQuestionsForTemplate(template_id)
    return buildQuestionsForm(questions,readOnly=True)

def survey_getAllSectionsForTemplate(template_id):
    """
        function to return the list of sections for the given template
        The sections are returned in the order of their position in the
        template.

        The data on each section is held in a dict and is as follows:
        section_id, name, template_id, and posn
    """
    s3db = current.s3db
    db = current.db
    sectable = s3db.survey_section
    query = (sectable.template_id == template_id)

    rows = db(query).select(sectable.id,
                            sectable.name,
                            sectable.template_id,
                            sectable.posn,
                            orderby = sectable.posn)
    sections = []
    for sec in rows:
        sections.append({"section_id": sec.id,
                         "name" : sec.name,
                         "template_id": sec.template_id,
                         "posn" : sec.posn
                        }
                       )
    return sections


def getWidgetFromQuestion(question_id):
    """
        Function that gets the right widget for the question
    """
    s3db = current.s3db
    db = current.db
    qtable = s3db.survey_question
    query = (qtable.id == question_id)
    question = db(query).select(qtable.type,
                                limitby=(0, 1)).first()
    qstnType = question.type
    widgetObj = survey_question_type[qstnType](question_id)
    return widgetObj


def buildQuestionsForm(questions, complete_id=None, readOnly=False):
    # Create the form, hard-coded table layout :(
    T = current.T

    form = FORM()
    table = None
    sectionTitle = ""
    for question in questions:
        if sectionTitle != question["section"]:
            if table != None:
                form.append(table)
                form.append(P())
                form.append(HR(_width="90%"))
                form.append(P())
            table = TABLE()
            table.append(TR(TH(question["section"],
                               _colspan="2"),
                            _class="survey_section"))
            sectionTitle = question["section"]
        widgetObj = getWidgetFromQuestion(question["qstn_id"])
        if readOnly:
            table.append(TR(TD(question["code"]),
                            TD(widgetObj.type_represent()),
                            TD(question["name"])
                           )
                        )
        else:
            if complete_id != None:
                widgetObj.loadAnswer(complete_id, question["qstn_id"])
            widget = widgetObj.display(question_id = question["qstn_id"])
            if widget != None:
                table.append(widget)
    form.append(table)
    if not readOnly:
        button = INPUT(_type="submit", _name="Save", _value=T("Save"))
        form.append(button)
    return form

def survey_build_template_summary(template_id):
    T = current.T
    s3 = current.response.s3

    table = TABLE(_id="template_summary",
                  _class="dataTable display")
    hr = TR(TH(T("Position")), TH(T("Section")))
    qstnTypeList = {}
    posn = 1
    for (key, type) in survey_question_type.items():
        hr.append(TH(type().type_represent()))
        qstnTypeList[key] = posn
        posn += 1
    hr.append(TH(T("Total")))
    header = THEAD(hr)

    numOfQstnTypes = len(survey_question_type) + 1
    questions = survey_getAllQuestionsForTemplate(template_id)
    sectionTitle = ""
    line = []
    body = TBODY()
    section = 0
    total = ["", T("Total")] + [0]*numOfQstnTypes
    for question in questions:
        if sectionTitle != question["section"]:
            if line != []:
                br = TR()
                for cell in line:
                    br.append(cell)
                body.append(br)
            section += 1
            sectionTitle = question["section"]
            line = [section, sectionTitle] + [0]*numOfQstnTypes
        line[qstnTypeList[question["type"]]+1] += 1
        line[numOfQstnTypes+1] += 1
        total[qstnTypeList[question["type"]]+1] += 1
        total[numOfQstnTypes+1] += 1
    # Add the trailing row
    br = TR()
    for cell in line:
        br.append(cell)
    body.append(br)
    # Add the footer to the table
    foot = TFOOT()
    tr = TR()
    for cell in total:
        tr.append(TD(B(cell))) # don't use TH() otherwise dataTables will fail
    foot.append(tr)


    table.append(header)
    table.append(body)
    table.append(foot)
    # turn off server side pagination
    s3.no_sspag = True
    # send the id of the table
    s3.dataTableID = "template_summary"
    return table




class S3QuestionModel(S3Model):
    """
        Question Model
    """

    names = ["survey_question",
             "survey_question_metadata",
             "survey_question_list"
            ]

    def model(self):

        db = current.db
        T = current.T
        s3 = current.response.s3

        """ The survey_question table defines a question that will appear
            within a section, and thus belong to the template.

            This holds the actual question and
            A string code (unique within the template) is used to identify the question.

            It will have a type from the questionType dictionary.
            This type will determine the options that can be associated with it.
            A question can belong to many different sections.
            The notes are to help the enumerator and will typically appear as a
            footnote in the printed form.
        """
        tablename = "survey_question"
        table = self.define_table(tablename,
                                 Field("name",
                                       "string",
                                       length=200,
                                       notnull=True,
                                       ),
                                 Field("code",
                                       "string",
                                       length=16,
                                       notnull=True,
                                       ),
                                 Field("notes",
                                       "string",
                                       length=400
                                       ),
                                 Field("type",
                                       "string",
                                       length=40,
                                       notnull=True,
                                       ),
                                 Field("metadata",
                                       "text",
                                      ),
                                 *s3.meta_fields()
                               )

        # CRUD Strings
        s3.crud_strings[tablename] = Storage(
            title_create = T("Add an Assessment Question"),
            title_display = T("Assessment Question Details"),
            title_list = T("List of Assessment Questions"),
            title_update = T("Edit Assessment Question"),
            subtitle_create = T("Add a new Assessment Question"),
            subtitle_list = T("Assessment Templates"),
            label_list_button = T("List all Assessment Questions"),
            label_create_button = T("Add a new Assessment Question"),
            label_delete_button = T("Delete this Assessment Question"),
            msg_record_created = T("Assessment Question added"),
            msg_record_modified = T("Assessment Question updated"),
            msg_record_deleted = T("Assessment Question deleted"),
            msg_list_empty = T("No Assessment Questions currently registered"))

        self.configure(tablename,
                        onvalidation = self.question_onvalidate,
                        onaccept = self.question_onaccept,
                        deduplicate = self.survey_question_duplicate,
                        )


        """
            The survey_question_metadata table is referenced by
            the survey_question table and is used to manage
            the metadata that will be associated with a question type.
            For example: if the question type is option, then valid metadata
            might be:
            count: the number of options that will be presented: 3
            1 : the first option                               : Female
            2 : the second option                              : Male
            3 : the third option                               : Not Specified
            So in the above case a question record will be associated with four
            question_metadata records.
        """
        tablename = "survey_question_metadata"
        table = self.define_table(tablename,
                                 Field("question_id",
                                       "reference survey_question",
                                       readable=False,
                                       writable=False
                                       ),
                                 Field("descriptor",
                                       "string",
                                       length=20,
                                       notnull=True,
                                       ),
                                 Field("value",
                                       "text",
                                       notnull=True,
                                       ),
                                 *s3.meta_fields()
                               )

        # CRUD Strings
        s3.crud_strings[tablename] = Storage(
            title_create = T("Add Question Meta-Data"),
            title_display = T("Question Meta-Data Details"),
            title_list = T("List of Question Meta-Data"),
            title_update = T("Edit Question Meta-Data"),
            subtitle_create = T("Add new Question Meta-Data"),
            subtitle_list = T("Question Meta-Data"),
            label_list_button = T("List all Question Meta-Data"),
            label_create_button = T("Add new Question Meta-Data"),
            label_delete_button = T("Delete this Question Meta-Data"),
            msg_record_created = T("Question Meta-Data added"),
            msg_record_modified = T("Question Meta-Data updated"),
            msg_record_deleted = T("Question Meta-Data deleted"),
            msg_list_empty = T("No Question Meta-Data currently registered"),
            title_upload = T("Upload a Question List import file")
            )

        self.configure(tablename,
                       deduplicate = self.survey_question_metadata_duplicate
                      )

        """ The survey_question_list table is a resolver between
            the survey_question and the survey_section tables.

            Along with ids mapping back to these tables
            it will have a code that can be used to reference the question
            it will have the position that the question will appear in the template
        """
        tablename = "survey_question_list"
        template_id = self.survey_template_id
        table = self.define_table(tablename,
                                 Field("posn",
                                       "integer",
                                       notnull=True,
                                       ),
                                 template_id(),
                                 Field("question_id",
                                       "reference survey_question",
                                       readable=False,
                                       writable=False
                                       ),
                                 Field("section_id",
                                       "reference survey_section",
                                       readable=False,
                                       writable=False
                                       ),
                                 *s3.meta_fields()
                               )

        # CRUD Strings
        s3.crud_strings[tablename] = Storage(
            title_upload = T("Upload an Assessment Template import file")
            )

        self.configure(tablename,
                        onaccept = self.question_list_onaccept,
                        deduplicate = self.survey_question_list_duplicate,
                        )
        # ---------------------------------------------------------------------
        return Storage()


    @staticmethod
    def question_onvalidate(form):
        """
            Any text with the metadata that is imported will be held in
            single quotes, rather than double quotes and so these need
            to be escaped to double quotes to make it valid JSON
        """
        from xml.sax.saxutils import unescape
        if form.vars.metadata != None:
            form.vars.metadata = unescape(form.vars.metadata,{"'":'"'})
        return True

    @staticmethod
    def question_onaccept(form):
        """
            All of the question metadata will be stored in the metadata
            field in a JSON format.
            They will then be inserted into the survey_question_metadata
            table pair will be a record on that table.

        """
        s3db = current.s3db

        if form.vars.metadata == None:
            return
        qstntable = s3db.survey_question
        if form.vars.id:
            record = qstntable[form.vars.id]
        else:
            return
        if form.vars.metadata \
        and form.vars.metadata != "" \
        and form.vars.metadata != "None":
            survey_updateMetaData(record,
                                  form.vars.type,
                                  form.vars.metadata
                                 )

    @staticmethod
    def survey_question_duplicate(job):
        """
          Rules for finding a duplicate:
           - Look for the question code
        """
        # ignore this processing if the id is set
        if job.id:
            return
        if job.tablename == "survey_question":
            table = job.table
            code = "code" in job.data and job.data.code
            query = (table.code == code)
            return duplicator(job, query)


    @staticmethod
    def survey_question_metadata_duplicate(job):
        """
          Rules for finding a duplicate:
           - Look for the question_id and descriptor
        """
        # ignore this processing if the id is set
        if job.tablename == "survey_question_metadata":
            table = job.table
            question = "question_id" in job.data and job.data.question_id
            descriptor  = "descriptor" in job.data and job.data.descriptor
            query = (table.descriptor == descriptor) & \
                    (table.question_id == question)
            return duplicator(job, query)


    @staticmethod
    def question_list_onaccept(form):
        """
            If a grid question is added to the the list then all of the
            grid children will need to be added as well
        """
        db = current.db
        s3db = current.s3db

        qstntable = s3db.survey_question
        try:
            question_id = form.vars.question_id
            template_id = form.vars.template_id
            section_id = form.vars.section_id
            posn = form.vars.posn
        except:
            return
        record = qstntable[question_id]
        type = record.type
        if type == "Grid":
            widgetObj = survey_question_type["Grid"]()
            widgetObj.insertChildrenToList(question_id,
                                           template_id,
                                           section_id,
                                           posn,
                                          )
        if type == "Location":
            widgetObj = survey_question_type["Location"]()
            widgetObj.insertChildrenToList(question_id,
                                           template_id,
                                           section_id,
                                           posn,
                                          )

    @staticmethod
    def survey_question_list_duplicate(job):
        """
          Rules for finding a duplicate:
           - The template_id, question_id and section_id are the same
        """
        # ignore this processing if the id is set
        if job.tablename == "survey_question_list":
            table = job.table
            tid = "template_id" in job.data and job.data.template_id
            qid = "question_id" in job.data and job.data.question_id
            sid = "section_id" in job.data and job.data.section_id
            query = (table.template_id == tid) & \
                    (table.question_id == qid) & \
                    (table.section_id == sid)
            return duplicator(job, query)

def survey_getQuestionFromCode(code, series_id=None):
    """
        function to return the question for the given series
        with the code that matches the one passed in
    """
    s3db = current.s3db
    db = current.db

    sertable = s3db.survey_series
    q_ltable = s3db.survey_question_list
    qsntable = s3db.survey_question
    if series_id != None:
        query = db((sertable.id == series_id) & \
                   (q_ltable.template_id == sertable.template_id) & \
                   (q_ltable.question_id == qsntable.id) & \
                   (qsntable.code == code)
                  )
    else:
        query = db((q_ltable.template_id == sertable.template_id) & \
                   (q_ltable.question_id == qsntable.id) & \
                   (qsntable.code == code)
                  )
    record = query.select(qsntable.id,
                          qsntable.code,
                          qsntable.name,
                          qsntable.type,
                          q_ltable.posn,
                          limitby=(0, 1)).first()
    question = {}
    if record != None:
        question["qstn_id"] = record.survey_question.id
        question["code"] = record.survey_question.code
        question["name"] = record.survey_question.name
        question["type"] = record.survey_question.type
        question["posn"] = record.survey_question_list.posn
    return question

def survey_getAllQuestionsForTemplate(template_id):
    """
        function to return the list of questions for the given template
        The questions are returned in the order of their position in the
        template.

        The data on a question that it returns is as follows:
        qstn_id, code, name, type, posn, section
    """
    s3db = current.s3db
    db = current.db

    sectable = s3db.survey_section
    q_ltable = s3db.survey_question_list
    qsntable = s3db.survey_question
    query = db((q_ltable.template_id == template_id) & \
               (q_ltable.section_id == sectable.id) & \
               (q_ltable.question_id == qsntable.id)
              )
    rows = query.select(qsntable.id,
                        qsntable.code,
                        qsntable.name,
                        qsntable.type,
                        sectable.name,
                        q_ltable.posn,
                        orderby=(q_ltable.posn))
    questions = []
    for row in rows:
        question = {}
        question["qstn_id"] = row.survey_question.id
        question["code"] = row.survey_question.code
        question["name"] = row.survey_question.name
        question["type"] = row.survey_question.type
        question["posn"] = row.survey_question_list.posn
        question["section"] = row.survey_section.name
        questions.append(question)
    return questions

def survey_getAllQuestionsForSeries(series_id):
    """
        function to return the list of questions for the given series
        The questions are returned in to order of their position in the
        template.

        The data on a question that is returns is as follows:
        qstn_id, code, name, type, posn, section
    """
    s3db = current.s3db
    db = current.db

    sertable = s3db.survey_series
    query = db((sertable.id == series_id))
    row = query.select(sertable.template_id, limitby=(0, 1)).first()
    template_id = row.template_id
    questions = survey_getAllQuestionsForTemplate(template_id)
    return questions

def survey_getAllQuestionsForComplete(complete_id):
    """
        function to return a tuple of the list of questions and series_id
        for the given completed_id

        The questions are returned in to order of their position in the
        template.

        The data on a question that is returns is as follows:
        qstn_id, code, name, type, posn, section
    """
    s3db = current.s3db
    db = current.db

    comtable = s3db.survey_complete
    query = db((comtable.id == complete_id))
    row = query.select(comtable.series_id, limitby=(0, 1)).first()
    series_id = row.series_id
    questions = survey_getAllQuestionsForSeries(series_id)
    return (questions, series_id)

def survey_get_series_questions_of_type(questionList, type):
    if isinstance(type, (list, tuple)):
        types = type
    else:
        types = (type)
    questions = []
    for question in questionList:
        if question["type"] in types:
            questions.append(question)
        elif question["type"] == "Link" or \
             question["type"] == "GridChild":
            widgetObj = getWidgetFromQuestion(question["qstn_id"])
            if widgetObj.getParentType() in types:
                question["name"] = widgetObj.fullName()
                questions.append(question)
    return questions

def survey_getQuestionFromName(name, series_id):
    """
        function to return the question for the given series
        with the name that matches the one passed in
    """
    s3db = current.s3db
    db = current.db

    sertable = s3db.survey_series
    q_ltable = s3db.survey_question_list
    qsntable = s3db.survey_question
    query = db((sertable.id == series_id) & \
               (q_ltable.template_id == sertable.template_id) & \
               (q_ltable.question_id == qsntable.id) & \
               (qsntable.name == name)
              )
    record = query.select(qsntable.id,
                          qsntable.code,
                          qsntable.name,
                          qsntable.type,
                          q_ltable.posn,
                          limitby=(0, 1)).first()
    question = {}
    question["qstn_id"] = record.survey_question.id
    question["code"] = record.survey_question.code
    question["name"] = record.survey_question.name
    question["type"] = record.survey_question.type
    question["posn"] = record.survey_question_list.posn
    return question


def survey_updateMetaData (record, type, metadata):
    import gluon.contrib.simplejson as json
    db = current.db
    s3db = current.s3db

    metatable = s3db.survey_question_metadata
    id = record.id
    # the metadata can either be passed in as a JSON string
    # or as a parsed map. If it is a string load the map.
    if isinstance(metadata, str):
        metadataList = json2py(metadata)
    else:
        metadataList = metadata
    for (desc, value) in metadataList.items():
            desc = desc.strip()
            if not isinstance(value, str):
                # web2py stomps all over a list so convert back to a string
                # before inserting it on the database
                value = json.dumps(value)
            value = value.strip()
            metatable.insert(question_id = id,
                             descriptor = desc,
                             value = value
                            )
    if type == "Grid":
        widgetObj = survey_question_type["Grid"]()
        widgetObj.insertChildren(record, metadataList)




class S3FormatterModel(S3Model):
    """
        The survey_formatter table defines the order in which the questions
        will be laid out when a formatted presentation is used.

        The idea is to be able to present the questions in a format that
        best uses the available space and is familiar to those using the
        tool.

        Examples of formatted presentation are the spreadsheet and the web
        form. This may be extended to PDF documents.

        The rules are held as a JSON record and describe where each question
        within the section should appear in terms of rows and columns. Each
        question is referenced by the question code.

        For example assume a section with the following eight questions:
        QSTN_1, QSTN_2, QSTN_3, QSTN_4, QSTN_5, QSTN_6, QSTN_7, QSTN_8
        Then to display them in three rows:
        [[QSTN_1, QSTN_2, QSTN_3], [QSTN_4, QSTN_5, QSTN_6], [QSTN_7, QSTN_8]]
        would present it as follows:
        QSTN_1, QSTN_2, QSTN_3,
        QSTN_4, QSTN_5, QSTN_6,
        QSTN_7, QSTN_8
        The order of the questions does not need to be preserved, thus:
        [[QSTN_1, QSTN_2], [QSTN_4, QSTN_5, QSTN_3], [QSTN_7, QSTN_8, QSTN_6]]
        would be valid, and give:
        QSTN_1, QSTN_2,
        QSTN_4, QSTN_5, QSTN_3,
        QSTN_7, QSTN_8, QSTN_6,

        ***NOTE***
        When importing this record with a CSV file the question code will be
        single quoted, rather than double quoted which JSON requires.
        This is because the whole rule needs to be double quoted. Code that
        extracts the records from the table will then need to change all
        single quotes to double quotes. This can be done as follows:

        rowList = json2py(rules)

    """
    names = ["survey_formatter"]
    def model(self):

        db = current.db
        T = current.T
        s3 = current.response.s3

        template_id = self.survey_template_id
        survey_formatter_methods = {
            1: T("Default"),
            2: T("Web Form"),
            3: T("Spreadsheet"),
            4: T("PDF"),
        }

        tablename = "survey_formatter"
        table = self.define_table(tablename,
                                template_id(),
                                Field("section_id",
                                       "reference survey_section",
                                       readable=False,
                                       writable=False
                                       ),
                                Field("method",
                                      "integer",
                                      requires = IS_IN_SET(survey_formatter_methods,
                                                           zero=None),
                                      default=1,
                                      represent = lambda index: survey_formatter_methods[index],
                                      readable=True,
                                      writable=False),
                                Field("rules", "text", default=""),
                                 *s3.meta_fields()
                               )

        self.configure(tablename,
                        onaccept = self.formatter_onaccept,
                        deduplicate=self.survey_formatter_duplicate
                        )

        # ---------------------------------------------------------------------
        return Storage()

    @staticmethod
    def formatter_onaccept(form):
        """
            If this is the formatter rules for the Background Information
            section then add the standard questions to the layout
        """
        import gluon.contrib.simplejson as json
        db = current.db
        s3db = current.s3db

        section_id = form.vars.section_id
        sectionTbl = s3db.survey_section
        section_name = sectionTbl[section_id].name
        if section_name == "Background Information":
            col1 = []
            # Add the default layout
            templateTbl = s3db.survey_template
            template = templateTbl[form.vars.template_id]
            if template.competion_qstn != "":
                col1.append("STD-WHO")
            if template.date_qstn != "":
                col1.append("STD-DATE")
            if template.time_qstn != "":
                col1.append("STD-TIME")
            if "location_detail" in template:
                col2 = ["STD-P-Code"]
                locationList = json2py(template.location_detail)
                for loc in locationList:
                    col2.append("STD-%s" % loc)
                col = [col1, col2]
                rule = [{"columns":col}]
                ruleList = json2py(form.vars.rules)
                ruleList[:0]=rule
                rules = json.dumps(ruleList)
                ftable = db.survey_formatter
                db(ftable.id == form.vars.id).update(rules = rules)

    @staticmethod
    def survey_formatter_duplicate(job):
        """
          Rules for finding a duplicate:
           - Look for a record with the same template_id and section_id
        """
        if job.tablename == "survey_formatter":
            table = job.table
            tid = "template_id" in job.data and job.data.template_id
            sid = "section_id" in job.data and job.data.section_id
            query = (table.template_id == tid) & \
                    (table.section_id == sid)
            return duplicator(job, query)

def survey_getQstnLayoutRules(template_id,
                       section_id,
                       method = 1
                      ):
    """
        This will return the rules for laying out the questions for
        the given section within the template.
        This is used when generating a formatted layout.

        First it will look for a survey_formatter record that matches
        the method given. Failing that it will look for a default
        survey_formatter record. If no appropriate survey_formatter
        record exists for the section then it will use the posn
        field found in the survey_question_list record.

        The function will return a list of rows. Each row is a list
        of question codes.
    """
    s3db = current.s3db
    db = current.db

    # search for layout rules on the survey_formatter table
    fmttable = s3db.survey_formatter
    query = db((fmttable.template_id == template_id) & \
               (fmttable.section_id == section_id)
              )
    rows = query.select(fmttable.method,
                        fmttable.rules,
                       )
    rules = None
    drules = None # default rules
    for row in rows:
        if row.method == method:
            rules = row.rules
            break
        elif row.method == 1:
            drules = row.rules
    if rules == None and drules != None:
        rules = drules
    rowList = []
    if rules == None or rules == "":
        # get the rules from survey_question_list
        q_ltable = s3db.survey_question_list
        qsntable = s3db.survey_question
        query = db((q_ltable.template_id == template_id) & \
                   (q_ltable.section_id == section_id) & \
                   (q_ltable.question_id == qsntable.id)
                  )
        rows = query.select(qsntable.code,
                            q_ltable.posn,
                            orderby=(q_ltable.posn))
        for qstn in rows:
            rowList.append([qstn.survey_question.code])
    else:
        # convert the JSON rules to python
        rowList = json2py(rules)
    return rowList


class S3SeriesModel(S3Model):
    """
        Series Model
    """

    names = ["survey_series"]

    def model(self):

        db = current.db
        T = current.T
        s3 = current.response.s3
        settings = current.deployment_settings

        series_status = {
            1: T("Active"),
            2: T("Closed"),
        }
        """
            The survey_series table is used to hold all uses of a template

            When a series is first created the template status will change from
            Pending to Active and at the stage no further changes to the
            template can be made.

            Typically a series will be created for an event, which may be a
            response to a natural disaster, an exercise,
            or regular data collection activity.

            The series is a container for all the responses for the event
        """
        tablename = "survey_series"
        template_id = self.survey_template_id
        person_id = self.pr_person_id
        organisation_id = self.org_organisation_id
        s3_date_represent = S3DateTime.date_represent
        s3_date_format = settings.get_L10n_date_format()

        table = self.define_table(tablename,
                                 Field("name", "string",
                                       default="",
                                       length=120,
                                       requires = IS_NOT_EMPTY()),
                                 Field("description", "text", default="", length=500),
                                 Field("status",
                                       "integer",
                                       requires = IS_IN_SET(series_status,
                                                            zero=None),
                                       default=1,
                                       represent = lambda index: series_status[index],
                                       readable=True,
                                       writable=False),
                                 template_id(empty=False),
                                 person_id(),
                                 organisation_id(widget = S3OrganisationAutocompleteWidget(default_from_profile = True)),
                                 Field("logo", "string", default="", length=512),
                                 Field("language", "string", default="en", length=8),
                                 Field("start_date",
                                       "date",
                                       requires = IS_EMPTY_OR(IS_DATE(format = s3_date_format)),
                                       represent = s3_date_represent,
                                       default=None),
                                 Field("end_date", "date", default=None),
                                 *s3.meta_fields())

        # CRUD Strings
        s3.crud_strings[tablename] = Storage(
            title_create = T("Conduct an Event Assessment"),
            title_display = T("Details of Event Assessment"),
            title_list = T("List of Event Assessments"),
            title_update = T("Edit this Event Assessment"),
            title_analysis_summary = T("Event Assessment Summary"),
            title_analysis_chart = T("Event Assessment Chart"),
            title_map = T("Event Assessment Map"),
            subtitle_create = T("Add a new Event Assessment"),
            subtitle_list = T("Event Assessment"),
            subtitle_analysis_summary = T("Summary of Event Assessment Responses"),
            help_analysis_summary = T("Click on a question to select it then click 'Display Selected Questions' button to view all event assessment responses for only the selected questions"),
            subtitle_analysis_chart = T("Select a label question and at least one numeric question to display the chart."),
            subtitle_map = T("Event Assessment Map"),
            label_list_button = T("List of Event Assessment"),
            label_create_button = T("Add a new Event Assessment"),
            label_delete_button = T("Delete this Event Assessment"),
            msg_record_created = T("Event Assessment added"),
            msg_record_modified = T("Event Assessment updated"),
            msg_record_deleted = T("Event Assessment deleted"),
            msg_list_empty = T("No Event Assessments currently registered"))

        self.configure(tablename,
                        create_next = URL(f="newAssessment",
                                          vars={"viewing":"survey_series.[id]"}),
                        onaccept = self.series_onaccept,
                        deduplicate = self.survey_series_duplicate,
                        )

        self.add_component(table, survey_template="template_id")
        self.add_component("survey_complete",
                           survey_series = "series_id"
                          )

        self.set_method("survey_series", method="summary", action=self.seriesSummary)
        self.set_method("survey_series", method="graph", action=self.seriesGraph)
        self.set_method("survey_series", method="map", action=self.seriesMap)
        self.set_method("survey_series",
                        method="series_chart_download",
                        action=self.seriesChartDownload
                       )
        # Return names to response.s3
        return Storage(
            survey_series_status = series_status,
        )

    @staticmethod
    def series_onaccept(form):
        """
            Ensure that the template status is set to Active
        """
        db = current.db
        s3db = current.s3db
        table = s3db.survey_template

        if form.vars.template_id:
            template_id = form.vars.template_id
        else:
            return
        db(table.id == template_id).update(status = 2)

    @staticmethod
    def survey_series_duplicate(job):
        """
          Rules for finding a duplicate:
           - Look for a record with the same name, ignoring case
        """
        if job.tablename == "survey_series":
            table = job.table
            name = "name" in job.data and job.data.name
            query =  table.name.lower().like('%%%s%%' % name.lower())
            return duplicator(job, query)

    @staticmethod
    def seriesSummary(r, **attr):
        db = current.db
        s3db = current.s3db
        request = current.request
        s3 = current.response.s3

        # retain the rheader
        rheader = attr.get("rheader", None)
        if rheader:
            rheader = rheader(r)
            output = dict(rheader=rheader)
        else:
            output = dict()
        if request.env.request_method == "POST" \
           or "mode" in request.vars:
            # This means that the user has selected the questions and
            # Wants to display the details of the selected questions
            crud_strings = s3.crud_strings["survey_complete"]
            question_ids = []
            vars = request.vars

            if "mode" in vars:
                mode = vars["mode"]
                series_id = r.id
                if "selected" in vars:
                    selected = vars["selected"].split(",")
                else:
                    selected = []
                q_ltable = s3db.survey_question_list
                sertable = s3db.survey_series
                query = (sertable.id == series_id) & \
                        (sertable.template_id == q_ltable.template_id)
                questions = db(query).select(q_ltable.posn,
                                              q_ltable.question_id,
                                              orderby = q_ltable.posn)
                for question in questions:
                    if mode == "Inclusive":
                        if str(question.posn) in selected:
                            question_ids.append(str(question.question_id))
                    elif mode == "Exclusive":
                        if str(question.posn) not in selected:
                            question_ids.append(str(question.question_id))
                items = buildCompletedList(series_id, question_ids)
                if r.representation == "xls":
                    from ..s3.codecs.xls import S3XLS
                    exporter = S3XLS()
                    return exporter.encode(items,
                                           title=crud_strings.title_selected,
                                           use_colour=False
                                          )
                if r.representation == "html":
                    table = buildTableFromCompletedList(items)
#                        exporter = S3Exporter()
#                        table = exporter.html(items)
                output["items"] = table
                output["sortby"] = [[0,"asc"]]
                url_pdf = URL(c="survey",
                              f="series",
                              args=[series_id,"summary.pdf"],
                              vars = {"mode":mode,"selected":vars["selected"]}
                             )
                url_xls = URL(c="survey",
                              f="series",
                              args=[series_id,"summary.xls"],
                              vars = {"mode":mode,"selected":vars["selected"]}
                             )
                s3.formats["pdf"]=url_pdf
                s3.formats["xls"]=url_xls
            else:
                output["items"] = None
            output["title"] = crud_strings.title_selected
            output["subtitle"] = crud_strings.subtitle_selected
            output["help"] = ""
        else:
            crud_strings = s3.crud_strings["survey_series"]
            if "viewing" in request.vars:
                dummy, series_id = request.vars.viewing.split(".")
            elif "series" in request.vars:
                series_id = request.vars.series
            else:
                series_id = r.id
            form = survey_build_series_summary(series_id)
            output["items"] = form
            output["sortby"] = [[0, "asc"]]
            output["title"] = crud_strings.title_analysis_summary
            output["subtitle"] = crud_strings.subtitle_analysis_summary
            output["help"] = crud_strings.help_analysis_summary
            s3.dataTableSubmitLabelPosn = "top"
            s3.actions = None
        current.response.view = "survey/series_summary.html"
        return output

    @staticmethod
    def seriesGraph(r, **attr):
        """

            Allows the user to select one string question and multiple numeric
            questions. The string question is used to group the numeric data,
            with the result displayed as a bar chart.

            For example:
                The string question can be Geographic area, and the numeric
                questions could be people injured and families displaced.
                Then the results will be grouped by each geographical area.
        """
        s3 = current.response.s3
        request = current.request
        T = current.T

        def addQstnChkboxToTR(numQstnList, qstn):
            tr = TR()
            if numQstnList != None and qstn["code"] in numQstnList:
                tr.append(INPUT(_type="checkbox",
                                _name="numericQuestion",
                                _value=qstn["code"],
                                value=True,
                               )
                          )
            else:
                tr.append(INPUT(_type="checkbox",
                                _name="numericQuestion",
                                _value=qstn["code"],
                               )
                          )
            tr.append(LABEL(qstn["name"]))
            return tr

        # retain the rheader
        rheader = attr.get("rheader", None)
        if rheader:
            rheader = rheader(r)
            output = dict(rheader=rheader)
        else:
            output = dict()

        crud_strings = s3.crud_strings["survey_series"]
        # Draw the chart
        if "viewing" in request.vars:
            dummy, series_id = request.vars.viewing.split(".")
        elif "series" in request.vars:
            series_id = request.vars.series
        else:
            series_id = r.id
        debug = "Series ID %s<br />" % series_id
        numQstnList = None
        labelQuestion = None
        if "post_vars" in request and len(request.post_vars) > 0:
            if "labelQuestion" in request.post_vars:
                labelQuestion = request.post_vars.labelQuestion
            if "numericQuestion" in request.post_vars:
                numQstnList = request.post_vars.numericQuestion
                if not isinstance(numQstnList,(list,tuple)):
                    numQstnList = [numQstnList]
            debug += "Label: %s<br />Numeric: %s<br />" % (labelQuestion, numQstnList)
            if (numQstnList != None) and (labelQuestion != None):
                S3SeriesModel.drawChart(output, series_id, numQstnList, labelQuestion)
                if request.ajax == True:
                    return output["chart"].xml()
        #output["debug"] = debug

        # Build the form
        if series_id == None:
            return output
        allQuestions = survey_getAllQuestionsForSeries(series_id)
        labelTypeList = ("String",
                         "Option",
                         "YesNo",
                         "YesNoDontKnow",
                         "Location",
                         )
        labelQuestions = survey_get_series_questions_of_type (allQuestions, labelTypeList)
        lblQstns = []
        for question in labelQuestions:
            lblQstns.append(question["name"])
        numericTypeList = ("Numeric")

        form = FORM(_id="mapGraphForm")
        table = TABLE()

        labelQstn = SELECT(lblQstns, _name="labelQuestion", value=labelQuestion)
        table.append(TR(TH(T("Select Label Question:")), _class="survey_question"))
        table.append(labelQstn)

        table.append(TR(TH(T("Select Numeric Questions (one or more):")), _class="survey_question"))
        # First add the special questions
        specialQuestions = [{"code":"Count", "name" : T("Number or Responses")}]
        innerTable = TABLE()
        for qstn in specialQuestions:
            tr = addQstnChkboxToTR(numQstnList, qstn)
            innerTable.append(tr)
        table.append(innerTable)
        # Now add the numeric questions
        numericQuestions = survey_get_series_questions_of_type (allQuestions, numericTypeList)
        innerTable = TABLE()
        for qstn in numericQuestions:
            tr = addQstnChkboxToTR(numQstnList, qstn)
            innerTable.append(tr)
        table.append(innerTable)
        form.append(table)

        series = INPUT(_type="hidden",
                       _id="selectSeriesID",
                       _name="series",
                       _value="%s" % series_id
                      )
        button = INPUT(_type="button", _id="chart_btn", _name="Chart", _value=T("Display Chart"))
        form.append(series)
        form.append(button)
        # Set up the javascript code for ajax interaction
        jurl = URL(r=request, c=r.prefix, f=r.function, args=request.args)
        s3.jquery_ready.append("""
$("#chart_btn").click(function(){
var data = $("#mapGraphForm").serialize()
var url = "<a class='action-btn' href=series_chart_download?" + data + ">Download Chart</a>"
$.post('%s',
       data,
       function(data) {
                        $("#survey_chart").empty();
                        $("#survey_chart").append(data);
                        $("#survey_chart_download").empty();
                        $("#survey_chart_download").append(url);
                      }
      );
});
""" % jurl)
        output["showForm"] = P(T("Click on the chart to show/hide the form."))
        output["form"] = form
        output["title"] = crud_strings.title_analysis_chart
        current.response.view = "survey/series_analysis.html"
        return output

    @staticmethod
    def seriesMap(r, **attr):
        from datetime import datetime
        startTime = datetime.now()
        from s3survey import S3AnalysisPriority
        import math
        s3 = current.response.s3
        request = current.request
        T = current.T
        gis = current.gis

        # retain the rheader
        rheader = attr.get("rheader", None)
        if rheader:
            rheader = rheader(r)
            output = dict(rheader=rheader)
        else:
            output = dict()
        crud_strings = s3.crud_strings["survey_series"]
        if "viewing" in request.vars:
            dummy, series_id = request.vars.viewing.split(".")
        elif "series" in request.vars:
            series_id = request.vars.series
        else:
            series_id = r.id
        if series_id == None:
            seriesList = []
            records = survey_getAllSeries()
            for row in records:
                 seriesList.append(row.id)
        else:
            seriesList = [series_id]
        pqstn_name = None
        if "post_vars" in request and len(request.post_vars) > 0:
            if "pqstn_name" in request.post_vars:
                pqstn_name = request.post_vars.pqstn_name
        feature_queries = []
        bounds = {}

        # Set up the legend
        for series_id in seriesList:
            series_name = survey_getSeriesName(series_id)
            response_locations = getLocationList(series_id)
            if pqstn_name == None:
                pqstn = survey_getPriorityQuestionForSeries(series_id)
            else:
                pqstn = survey_getQuestionFromName(pqstn_name,
                                                      series_id)
            if pqstn != {}:
                pqstn_name = pqstn["name"]
                pqstn_id = pqstn["qstn_id"]
                answers = survey_getAllAnswersForQuestionInSeries(pqstn_id,
                                                                     series_id)
                analysisTool = survey_analysis_type["Numeric"](pqstn_id,
                                                               answers)
                analysisTool.advancedResults()
            else:
                analysisTool = None
            priorityObj = S3AnalysisPriority(range=[-.66, .66],
                                             colour={-1:"#888888", # grey
                                                     0:"#008000", # green
                                                     1:"#FFFF00", # yellow
                                                     2:"#FF0000", # red
                                                     },
                                              image={-1:"grey",
                                                      0:"green",
                                                      1:"yellow",
                                                      2:"red",
                                                    },
                                               desc={-1:"No Data",
                                                      0:"Low",
                                                      1:"Average",
                                                      2:"High",
                                                    },
                                              zero = True)
            if analysisTool != None and not math.isnan(analysisTool.mean):
                pBand = analysisTool.priorityBand(priorityObj)
                legend = TABLE(
                           TR (TH(T("Marker Levels"), _colspan=3),
                               _class= "survey_question"),
                           )
                for key in priorityObj.image.keys():
                    tr = TR( TD(priorityObj.imageURL(request.application,
                                                     key)),
                             TD(priorityObj.desc(key)),
                             TD(priorityObj.rangeText(key, pBand)),
                           )
                    legend.append(tr)
                output["legend"] = legend

            if len(response_locations) > 0:
                for i in range( 0 , len( response_locations) ):
                    complete_id = response_locations[i].complete_id
                    # Insert how we want this to appear on the map
                    url = URL(c="survey",
                              f="series",
                              args=[series_id,
                                    "complete",
                                    complete_id,
                                    "read"
                                    ]
                              )
                    response_locations[i].shape = "circle"
                    response_locations[i].size = 5
                    if analysisTool is None:
                        priority = -1
                    else:
                        priority = analysisTool.priority(complete_id,
                                                         priorityObj)
                    response_locations[i].colour = priorityObj.colour[priority]
                    response_locations[i].popup_url = url
                    response_locations[i].popup_label = response_locations[i].name
                feature_queries.append({ "name": "%s: Assessments" % series_name,
                                         "query": response_locations,
                                         "active": True })
                if bounds == {}:
                    bounds = (gis.get_bounds(response_locations))
                else:
                    new_bounds = gis.get_bounds(response_locations)
                    bounds = merge_bounds([bounds, new_bounds])
        if bounds == {}:
            bounds = gis.get_bounds()
        map = gis.show_map(feature_queries = feature_queries,
                           height = 600,
                           width = 720,
                           bbox = bounds,
                           collapsed = True,
                           catalogue_layers = True,
                          )
        allQuestions = survey_getAllQuestionsForSeries(series_id)
        numericTypeList = ("Numeric")
        numericQuestions = survey_get_series_questions_of_type(allQuestions,
                                                                  numericTypeList)
        numQstns = []
        for question in numericQuestions:
            numQstns.append(question["name"])

        form = FORM(_id="mapQstnForm")
        table = TABLE()

        priorityQstn = SELECT(numQstns, _name="pqstn_name",
                              value=pqstn_name)
        series = INPUT(_type="hidden",
                       _id="selectSeriesID",
                       _name="series",
                       _value="%s" % series_id
                      )
        table.append(TR(TH("%s:" % T("Display Question on Map")),
                        _class="survey_question"))
        table.append(priorityQstn)
        table.append(series)
        form.append(table)

        button = INPUT(_type="submit", _name="Chart",
                       _value=T("Update Map"))
# REMOVED until we have dynamic loading of maps.
#            button = INPUT(_type="button", _id="map_btn", _name="Map_Btn", _value=T("Select the Question"))
#            jurl = URL(r=request, c=r.prefix, f=r.function, args=request.args)
#            s3.jquery_ready=["""
#$("#map_btn").click(function(){
#    $.post('%s',
#           $("#mapQstnForm").serialize(),
#           function(data) {
#                            obj = jQuery.parseJSON(data);
#                            $("#survey_map-legend").empty();
#                            $("#survey_map-legend").append(obj.legend);
#                            alert (obj.map);
#                            $("#survey_map-container").empty();
#                            $("#survey_map-container").append(obj.map);
#                          }
#          );
#});
#""" % jurl]
        form.append(button)

        output["title"] = crud_strings.title_map
        output["subtitle"] = crud_strings.subtitle_map
        output["instructions"] = T("Click on a marker to see the Event Assessment Response")
        output["form"] = form
        output["map"] = map

        current.response.view = "survey/series_map.html"
        endTime = datetime.now()
        duration = endTime - startTime
        print duration
        return output

    @staticmethod
    def seriesChartDownload(r, **attr):
        s3 = current.response.s3
        response = current.response
        request = current.request
        from gluon.contenttype import contenttype

        output = dict()
        series_id = request.args[0]
        seriesName = survey_getSeriesName(series_id)
        if "labelQuestion" in request.get_vars:
            labelQuestion = request.get_vars.labelQuestion
        if "numericQuestion" in request.get_vars:
            numQstnList = request.get_vars.numericQuestion
            if not isinstance(numQstnList,(list,tuple)):
                numQstnList = [numQstnList]
        if (numQstnList != None) and (labelQuestion != None):
            S3SeriesModel.drawChart(output, series_id, numQstnList, labelQuestion, outputFormat="png")
        response.headers["Content-Type"] = contenttype(".png")
        filename = "%s_chart.png" % seriesName
        response.headers["Content-disposition"] = "attachment; filename=\"%s\"" % filename
        return output["chart"]

    @staticmethod
    def drawChart(output, series_id, numQstnList, labelQuestion, outputFormat=None):
        s3 = current.response.s3
        T = current.T
        request = current.request

        getAnswers = survey_getAllAnswersForQuestionInSeries
        gqstn = survey_getQuestionFromName(labelQuestion, series_id)
        gqstn_id = gqstn["qstn_id"]
        ganswers = getAnswers(gqstn_id, series_id)
        dataList = []
        legendLabels = []
        for numericQuestion in numQstnList:
            if numericQuestion == "Count":
                # get the count of replies for the label question
                gqstn_type = gqstn["type"]
                analysisTool = survey_analysis_type[gqstn_type](gqstn_id, ganswers)
                map = analysisTool.uniqueCount()
                label = map.keys()
                data = map.values()
                legendLabels.append(T("Count of Question"))
            else:
                qstn = survey_getQuestionFromCode(numericQuestion, series_id)
                qstn_id = qstn["qstn_id"]
                qstn_type = qstn["type"]
                answers = getAnswers(qstn_id, series_id)
                analysisTool = survey_analysis_type[qstn_type](qstn_id, answers)
                label = analysisTool.qstnWidget.question.name
                if len(label) > 20:
                    label = "%s..." % label[0:20]
                legendLabels.append(label)
                grouped = analysisTool.groupData(ganswers)
                aggregate = "Sum"
                filtered = analysisTool.filter(aggregate, grouped)
                (label, data) = analysisTool.splitGroupedData(filtered)
            if data != []:
                dataList.append(data)

        if dataList == []:
            output["chart"] = H4(T("There is insufficient data to draw a chart from the questions selected"))
        else:
            chart = S3Chart(width=7.2)
            chart.displayAsIntegers()
            chart.survey_bar(labelQuestion,
                             dataList,
                             label,
                             legendLabels)
            if outputFormat == None:
                image = chart.draw()
            else:
                image = chart.draw(output=outputFormat)
            output["chart"] = image
            chartLink = A("Download",
                         _href=URL(c="survey",
                                   f="series",
                                   args=request.args,
                                   vars=request.vars
                                  )
                         )
            output["chartDownload"] = chartLink

def survey_serieslist_dataTable_post(r):
    s3 = current.response.s3
    T = current.T

    S3CRUD.action_buttons(r)
    url = URL(c="survey",
              f="series",
              args=["[id]","summary"]
             )
    s3.actions = [
                   dict(label=str(T("Open")),
                        _class="action-btn",
                        url=url
                       ),
                  ]

def survey_series_represent(value):
    """
        This will display the series name, rather than the id
    """
    s3db = current.s3db
    table = s3db.survey_series

    db = current.db
    query = db((table.id == value))
    row = query.select(table.name, limitby=(0, 1)).first()
    return row.name

def survey_series_rheader(r, tabs=[]):
    """
        The series rheader
    """
    s3db = current.s3db
    db = current.db
    T = current.T
    s3 = current.response.s3
    request = current.request
    auth = current.auth

    if r.representation == "html":

        tablename, record = s3_rheader_resource(r)
        if not record:
            series_id = request.vars.series
            record = survey_getSeries(series_id)
        if record != None:
            # Tabs
            if auth.s3_has_permission("create", "survey_series"):
                tabs = [(T("Details"), None),
                        (T("Add New Response"), "newAssessment/"),
                        (T("Responses"), "complete"),
                        (T("Summary"), "summary"),
                        (T("Chart"), "graph"),
                        (T("Map"), "map"),
                        ]
            else:
                tabs = [(T("Details"), None),
                        (T("Summary"), "summary"),
                        (T("Chart"), "graph"),
                        (T("Map"), "map"),
                       ]

            completeTable = s3db["survey_complete"]
            rheader_tabs = s3_rheader_tabs(r, tabs)

            query = (completeTable.series_id == record.id)
            row = db(query).count()
            tsection = TABLE(_class="survey-complete-list")
            lblSection = T("Number of Event Assessment Responses")
            rsection = TR(TH(lblSection), TD(row))
            tsection.append(rsection)

            urlexport = URL(c="survey",
                            f="series_export_formatted",
                            args=[record.id]
                            )
            tranForm = FORM(_action=urlexport)
            translationList = survey_getAllTranslationsForSeries(record.id)
            if len(translationList) > 0:
                tranTable = TABLE()
                tr = TR()
                tr.append(INPUT(_type='radio',
                                _name='translationLanguage',
                                _value="Default",
                                _checked=True,
                               ))
                tr.append(LABEL("Default"))
                colCnt = 1
                for translation in translationList:
                    # include a maximum of 4 translation languages per row
                    if colCnt == 4:
                        tranTable.append(tr)
                        tr = TR()
                        colCnt = 0
                    tr.append(INPUT(_type='radio',
                                    _name='translationLanguage',
                                    _value=translation["code"],
                                   ))
                    tr.append(LABEL(translation["language"]))
                    colCnt += 1
                if colCnt != 0:
                    tranTable.append(tr)
                tranForm.append(tranTable)
            export_xls_btn = INPUT(_type="submit",
                                   _id="export_xls_btn",
                                   _name="Export_Spreadsheet",
                                   _value=T("Download Assessment Template Spreadsheet"),
                                   _class="action-btn"
                                  )
            tranForm.append(export_xls_btn)
            try:
                # only add the Export to Word button up if PyRTF is installed 
                from PyRTF import Document
                export_rtf_btn = INPUT(_type="submit",
                                       _id="export_rtf_btn",
                                       _name="Export_Word",
                                       _value=T("Download Assessment Template Word Document"),
                                       _class="action-btn"
                                      )
                tranForm.append(export_rtf_btn)
            except:
                pass
            urlimport = URL(c="survey",
                            f="export_all_responses",
                            args=[record.id],
                            )
            buttons = DIV (A(T("Export all completed responses"),
                             _href=urlimport,
                             _id="All_resposnes",
                             _class="action-btn"
                             ),
                          )


            rheader = DIV(TABLE(
                          TR(
                             TH("%s: " % T("Template")),
                             survey_template_represent(record.template_id),
                             TH("%s: " % T("Name")),
                             record.name,
                             TH("%s: " % T("Status")),
                             s3.survey_series_status[record.status],
                             ),
                              ),
                          tsection,
                          tranForm,
                          buttons,
                          rheader_tabs)
            return rheader
    return None

def survey_getSeries(series_id):
    """
        function to return the series from a series id
    """
    s3db = current.s3db
    db = current.db

    table = s3db.survey_series
    query = db((table.id == series_id))
    row = query.select(limitby=(0, 1)).first()
    return row


def survey_getSeriesName(series_id):
    """
        function to return the series from a series id
    """
    record = survey_getSeries(series_id)
    if record != None:
        return record.name
    return ""

def survey_getAllSeries():
    """
        function to return all the series on the database
    """
    s3db = current.s3db
    db = current.db

    table = s3db.survey_series
    row = db(table).select()
    return row

def survey_buildQuestionnaireFromSeries(series_id, complete_id=None):
    """
        build a form displaying all the questions for a given series_id
        If the complete_id is also provided then the responses to each
        completed question will also be displayed
    """
    questions = survey_getAllQuestionsForSeries(series_id)
    return buildQuestionsForm(questions, complete_id)

def survey_save_answers_for_series(series_id, complete_id, vars):
    """
        function to save the list of answers for a completed series
    """
    questions = survey_getAllQuestionsForSeries(series_id)
    return saveAnswers(questions, series_id, complete_id, vars)

def saveAnswers(questions, series_id, complete_id, vars):
    s3db = current.s3db
    db = current.db
    text = ""
    table = s3db.survey_complete
    for question in questions:
        code = question["code"]
        if (code in vars) and vars[code] != "":
            line = '"%s","%s"\n' % (code, vars[code])
            text += line
    if complete_id == None:
        # Insert into database
        id = table.insert(series_id = series_id, answer_list = text)
        S3CompleteModel.completeOnAccept(id)
        return id
    else:
        # Update the complete_id record
        db(table.id == complete_id).update(answer_list = text)
        S3CompleteModel.completeOnAccept(complete_id)
        return complete_id


def survey_getPriorityQuestionForSeries(series_id):
    templateRec = survey_getTemplateFromSeries(series_id)
    if templateRec != None:
        priorityQstnCode = templateRec["priority_qstn"]
        question = survey_getQuestionFromCode(priorityQstnCode, series_id)
        return question
    else:
        return None


def survey_build_series_summary(series_id):
    T = current.T
    s3 = current.response.s3

    table = TABLE(_id="series_summary",
                  _class="dataTable display")
    hr = TR(TH(T("Position")),
            TH(T("Question")),
            TH(T("Code")),
            TH(T("Type")),
            TH(T("Summary"))
           )
    header = THEAD(hr)

    questions = survey_getAllQuestionsForSeries(series_id)
    line = []
    body = TBODY()
    for question in questions:
        question_id = question["qstn_id"]
        widgetObj = getWidgetFromQuestion(question_id)
        br = TR()
        br.append(question["posn"])
        br.append(question["name"])
        br.append(question["code"])
        type = widgetObj.type_represent()
        answers = survey_getAllAnswersForQuestionInSeries(question_id,
                                                   series_id)
        analysisTool = survey_analysis_type[question["type"]](question_id,
                                                              answers)
        chart = analysisTool.chartButton(series_id)
        cell = TD()
        cell.append(type)
        if chart:
            cell.append(chart)
        br.append(cell)
        analysisTool.count()
        br.append(analysisTool.summary())

        body.append(br)

    table.append(header)
    table.append(body)

    # turn off server side pagination
    s3.no_sspag = True
    # send the id of the table
    s3.dataTableID = "series_summary"
    # turn multi-select on
    s3.dataTableSelectable = True
    s3.dataTablePostMethod = True
    s3.dataTableSubmitLabel = current.T("Display Selected Questions")
    series = INPUT(_type="hidden", _id="selectSeriesID", _name="series",
                _value="%s" % series_id)
    mode = INPUT(_type="hidden", _id="importMode", _name="mode",
                 _value="Inclusive")
    selected = INPUT(_type="hidden", _id="importSelected",
                     _name="selected", _value="")
    form = FORM(table, series, mode, selected)
    return form

class S3CompleteModel(S3Model):
    """
        Complete Model
    """

    names = ["survey_complete",
             "survey_answer",
            ]

    def model(self):

        db = current.db
        T = current.T
        s3 = current.response.s3
        """
            The survey_complete table holds all of the answers for a completed
            response. It has a link back to the series this response belongs to.

            Whilst this table holds all of the answers in a text field during
            the onaccept each answer is extracted and then stored in the
            survey_answer table. This process of moving the answers to a
            separate table makes it easier to analyse the answers
            for a given question across all responses.
        """
        tablename = "survey_complete"
        table = self.define_table(tablename,
                                Field("series_id",
                                       "reference survey_series",
                                       represent = survey_series_represent,
                                       label = T("Series"),
                                       readable=False,
                                       writable=False
                                       ),
                                Field("answer_list",
                                      "text",
                                      represent = survey_answer_list_represent
                                     ),
                                Field("location",
                                       "text",
                                       readable=False,
                                       writable=False
                                       ),
                                 *s3.meta_fields())

        # CRUD Strings
        s3.crud_strings[tablename] = Storage(
            title_create = T("Enter Event Assessment Response"),
            title_display = T("Event Assessment Response Details"),
            title_list = T("List of Event Assessment Responses"),
            title_update = T("Edit Event Assessment Response"),
            title_selected = T("List of Selected Event Assessment Questions"),
            subtitle_create = T("Enter Event Assessment Response"),
            subtitle_list = T("Event Assessment Responses"),
            subtitle_selected = T("Selected Event Assessment Questions"),
            label_list_button = T("List all Event Assessment Response"),
            label_create_button = T("Add a new Completed Assessment"),
            label_delete_button = T("Delete this Event Assessment Response"),
            msg_record_created = T("Event Assessment Response entered"),
            msg_record_modified = T("Event Assessment Response updated"),
            msg_record_deleted = T("Event Assessment Response deleted"),
            msg_list_empty = T("No Event Assessment Responses currently registered"),
            title_upload = T("Upload the Event Assessment Response import file")
            )

        self.configure(tablename,
                       onvalidation = self.complete_onvalidate,
                       onaccept = self.complete_onaccept,
                       deduplicate=self.survey_complete_duplicate,
                      )
        self.add_component("survey_complete",
                            survey_series = dict(joinby="series_id",
                                                 multiple=True)
                           )

        """
            The survey_answer table holds the answer for a single response
            of a given question.
        """
        tablename = "survey_answer"
        table = self.define_table(tablename,
                                Field("complete_id",
                                       "reference survey_complete",
                                       readable=False,
                                       writable=False
                                       ),
                                Field("question_id",
                                       "reference survey_question",
                                       readable=True,
                                       writable=False
                                       ),
                                Field("value",
                                       "text",
                                       readable=True,
                                       writable=True
                                       ),
                                *s3.meta_fields())

        s3.crud_strings[tablename] = Storage(
            title_create = T("Add Assessment Answer"),
            title_display = T("Assessment Answer Details"),
            title_list = T("List of Assessment Answers"),
            title_update = T("Edit Assessment Answer"),
            subtitle_create = T("Add a new Assessment Answer"),
            subtitle_list = T("Assessment Answer"),
            label_list_button = T("List all Assessment Answer"),
            label_create_button = T("Add a new Assessment Answer"),
            label_delete_button = T("Delete this Assessment Answer"),
            msg_record_created = T("Assessment Answer added"),
            msg_record_modified = T("Assessment Answer updated"),
            msg_record_deleted = T("Assessment Answer deleted"),
            msg_list_empty = T("No Assessment Answers currently registered"))

        self.configure(tablename,
                       onaccept = self.answer_onaccept,
                       deduplicate = self.survey_answer_duplicate
                      )
        # ---------------------------------------------------------------------
        return Storage()


    @staticmethod
    def extractAnswerFromAnswerList(answerList, qstnCode):
        """
            function to extract the answer for the question code
            passed in from the list of answers. This is in a CSV
            format created by the XSL stylesheet or by the function
            saveAnswers()
        """
        start = answerList.find(qstnCode)
        if start == -1:
            return None
        start = start+len(qstnCode)+3
        end = answerList.find('"',start)
        answer = answerList[start:end]
        return answer

    @staticmethod
    def complete_onvalidate(form):
        if "series_id" not in form.vars or form.vars.series_id == None:
            form.errors.series_id = T("Series details missing.")
            return False
        if "answer_list" not in form.vars or form.vars.answer_list == None:
            form.errors.answer_list = T("The answers are missing.")
            return False
        series_id = form.vars.series_id
        answer_list = form.vars.answer_list
        qstn_list = getAllQuestionsForSeries(series_id)
        qstns = []
        for qstn in qstn_list:
            qstns.append(qstn["code"])
        answerList = answer_list.splitlines(True)
        for answer in answerList:
            qstn_code = answer[1:answer.find('","')]
            if qstn_code not in qstns:
                msg = "%s: %s" % (T("Unknown question code"), qstn_code)
                if answer_list not in form.errors:
                    form.errors.answer_list = msg
                else:
                    form.errors.answer_list += msg
        return True

    @staticmethod
    def complete_onaccept(form):
        """
            All of the answers will be stored in the answer_list in the
            format "code","answer"
            They will then be inserted into the survey_answer table
            each item will be a record on that table.

            This will also extract the default location question as
            defined by the template and store this in the location field
        """
        if form.vars.id:
            S3CompleteModel.completeOnAccept(form.vars.id)

    @staticmethod
    def completeOnAccept(complete_id):
        s3db = current.s3db
        db = current.db
        ##################################################################
        # Get the basic data that is needed
        ##################################################################
        rtable = s3db.survey_complete
        atable = s3db.survey_answer
        record = rtable[complete_id]
        series_id = record.series_id
        if series_id == None:
            return
        ##################################################################
        # Save all the answers from answerList in the survey_answer table
        ##################################################################
        answerList = record.answer_list
        S3CompleteModel.importAnswers(complete_id, answerList)
        ##################################################################
        # Extract the default template location question and save the
        # answer in the location field
        ##################################################################
        templateRec = survey_getTemplateFromSeries(series_id)
        locDetails = templateRec["location_detail"]
        if not locDetails:
            return
        widgetObj = get_default_location(complete_id)
        db(rtable.id == complete_id).update(location = widgetObj.repr())
        locations = get_location_details(complete_id)
        S3CompleteModel.importLocations(locations)

    @staticmethod
    def importAnswers(id, list):
        """
            private function used to save the answer_list stored in
            survey_complete into answer records held in survey_answer
        """
        import csv
        import os
        try:
            from cStringIO import StringIO    # Faster, where available
        except:
            from StringIO import StringIO
        strio = StringIO()
        strio.write(list)
        strio.seek(0)
        s3mgr = current.manager
        answer = []
        reader = csv.reader(strio)
        for row in reader:
            if row != None:
                row.insert(0,id)
                answer.append(row)

        from tempfile import TemporaryFile
        csvfile = TemporaryFile()
        writer = csv.writer(csvfile)
        writer.writerow(["complete_id", "question_code", "value"])
        for row in answer:
            writer.writerow(row)
        csvfile.seek(0)
        xsl = os.path.join("applications",
                           current.request.application,
                           "static",
                           "formats",
                           "s3csv",
                           "survey",
                           "answer.xsl")
        resource = s3mgr.define_resource("survey", "answer")
        resource.import_xml(csvfile, stylesheet = xsl, format="csv",)

    @staticmethod
    def importLocations(location_dict):
        """
            private function used to save the locations to gis.location
        """
        import csv
        import os
        s3mgr = current.manager
        answer = []
        lastLocWidget = None
        codeList = ["STD-L0","STD-L1","STD-L2","STD-L3","STD-L4"]
        headingList = ["Country",
                       "ADM1_NAME",
                       "ADM2_NAME",
                       "ADM3_NAME",
                       "ADM4_NAME"
                      ]
        cnt = 0
        headings = []
        for loc in codeList:
            if loc in location_dict:
                answer.append(location_dict[loc].repr())
                lastLocWidget = location_dict[loc]
                headings.append(headingList[cnt])
            cnt += 1
        # Check that we have at least one location question answered
        if lastLocWidget == None:
            return
        codeList = ["STD-P-Code","STD-Lat","STD-Lon"]
        for loc in codeList:
            if loc in location_dict:
                answer.append(location_dict[loc].repr())
            else:
                answer.append("")

        from tempfile import TemporaryFile
        csvfile = TemporaryFile()
        writer = csv.writer(csvfile)
        headings += ["Code2", "Lat", "Lon"]
        writer.writerow(headings)
        writer.writerow(answer)
        csvfile.seek(0)
        xsl = os.path.join("applications",
                           current.request.application,
                           "static",
                           "formats",
                           "s3csv",
                           "gis",
                           "location.xsl")
        resource = s3mgr.define_resource("gis", "location")
        resource.import_xml(csvfile, stylesheet = xsl, format="csv",)

    @staticmethod
    def survey_complete_duplicate(job):
        """
          Rules for finding a duplicate:
           - Look for a record with the same name, answer_list
        """
        if job.tablename == "survey_complete":
            table = job.table
            answers = "answer_list" in job.data and job.data.answer_list
            query =  table.answer_list == answers
            try:
                return duplicator(job, query)
            except:
                # if this is part of an import then the select will throw an error
                # if the question code doesn't exist.
                # This can happen during an import if the wrong file is used.
                return


    @staticmethod
    def answer_onaccept(form):
        """
            Some question types may require additional processing
        """
        s3db = current.s3db
        db = current.db

        if form.vars.complete_id and form.vars.question_id:
            atable = s3db.survey_answer
            complete_id = form.vars.complete_id
            question_id = form.vars.question_id
            value = form.vars.value
            widgetObj = getWidgetFromQuestion(question_id)
            newValue = widgetObj.onaccept(value)
            if newValue != value:
                query = (atable.question_id == question_id) & \
                        (atable.complete_id == complete_id)
                db(query).update(value = newValue)

    @staticmethod
    def survey_answer_duplicate(job):
        """
          Rules for finding a duplicate:
           - Look for a record with the same complete_id and question_id
        """
        if job.tablename == "survey_answer":
            table = job.table
            qid = "question_id" in job.data and job.data.question_id
            rid = "complete_id" in job.data and job.data.complete_id
            query = (table.question_id == qid) & \
                    (table.complete_id == rid)
            return duplicator(job, query)


def survey_answerlist_dataTable_pre():
    # The answer list has been removed for the moment. Currently it
    # displays all answers for a summary it would be better to
    # be able to display just a few select answers
    s3mgr = current.manager
    list_fields = ["created_on", "series_id", "location", "modified_by"]
    s3mgr.configure("survey_complete", list_fields=list_fields)


def survey_answerlist_dataTable_post(r):
    s3 = current.response.s3
    T = current.T

    S3CRUD.action_buttons(r)
    s3.actions = [
                   dict(label=str(T("Open")),
                        _class="action-btn",
                        url=URL(c="survey",
                                f="series",
                                args=[r.id,"complete","[id]","update"])
                       ),
                  ]

def survey_answer_list_represent(value):
    """
        Display the answer list in a formatted table.
        Displaying the full question (rather than the code)
        and the answer.
    """
    s3db = current.s3db
    db = current.db

    qtable = s3db.survey_question
    answer_text = value
    list = answer_text.splitlines()
    result = TABLE()
    questions = {}
    for line in list:
        line = S3Codec.xml_decode(line)
        (question, answer) = line.split(",",1)
        question = question.strip("\" ")
        if question in questions:
            question = questions[question]
        else:
            query = (qtable.code == question)
            qstn = db(query).select(qtable.name, limitby=(0, 1)).first()
            if qstn == None:
                continue
            questions[question] = qstn.name
            question =  qstn.name
        answer = answer.strip("\" ")
        result.append(TR(TD(B(question)),TD(answer)))
    return result

def get_location_details(complete_id):
    """
        It will return a dict of values for all of the standard location
        questions that have been answered
    """
    s3db = current.s3db
    db = current.db
    locations = {}
    comtable = s3db.survey_complete
    qsntable = s3db.survey_question
    answtable = s3db.survey_answer
    query = ((answtable.question_id == qsntable.id) & \
             (answtable.complete_id == comtable.id))
    codeList = ["STD-P-Code",
                "STD-L0","STD-L1","STD-L2","STD-L3","STD-L4",
                "STD-Lat","STD-Lon"]
    for locCode in codeList:
        record = db(query & (qsntable.code == locCode)).select(qsntable.id,
                                                               limitby=(0, 1)).first()
        if record:
            widgetObj = getWidgetFromQuestion(record.id)
            widgetObj.loadAnswer(complete_id, record.id)
            locations[locCode] = widgetObj
    return locations

def get_default_location(complete_id):
    """
        It will check each standard location question in
        the hierarchy until either one is found or none are found
    """
    s3db = current.s3db
    db = current.db

    comtable = s3db.survey_complete
    qsntable = s3db.survey_question
    answtable = s3db.survey_answer
    query = ((answtable.question_id == qsntable.id) & \
             (answtable.complete_id == comtable.id))
    codeList = ["STD-L4","STD-L3","STD-L2","STD-L1","STD-L0"]
    for locCode in codeList:
        record = db(query & (qsntable.code == locCode)).select(qsntable.id,
                                                               limitby=(0, 1)).first()
        if record:
            widgetObj = getWidgetFromQuestion(record.id)
            break
    if record:
        widgetObj.loadAnswer(complete_id, record.id)
        return widgetObj
    else:
        return None


def survey_getAllAnswersForQuestionInSeries(question_id, series_id):
    """
        function to return all the answers for a given question
        from with a specified series
    """
    s3db = current.s3db
    db = current.db

    ctable = s3db.survey_complete
    atable = s3db.survey_answer
    query = db((atable.question_id == question_id) & \
               (atable.complete_id == ctable.id) & \
               (ctable.series_id == series_id)
              )
    rows = query.select(atable.id,
                        atable.value,
                        atable.complete_id,
                       )
    answers = []
    for row in rows:
        answer = {}
        answer["answer_id"] = row.id
        answer["value"] = row.value
        answer["complete_id"] = row.complete_id
        answers.append(answer)
    return answers

def buildTableFromCompletedList(dataSource):
    s3 = current.response.s3

    headers = dataSource[0]
    items = dataSource[2:]

    table = TABLE(_id="completed_list",
                  _class="dataTable display")
    hr = TR()
    for title in headers:
        hr.append(TH(title))
    header = THEAD(hr)

    body = TBODY()

    for row in items:
        tr = TR()
        for answer in row:
            tr.append(TD(answer))
        body.append(tr)

    table.append(header)
    table.append(body)
    # turn off server side pagination
    s3.no_sspag = True
    # send the id of the table
    s3.dataTableID = "completed_list"
    return table

def buildCompletedList(series_id, question_id_list):
    """
        build a list of completed items for the series including
        just the questions in the list passed in

        The list will come in three parts.
        1) The first row is the header (list of field labels)
        2) The seconds row is the type of each column
        3) The remaining rows are the data

        @param series_id: The id of the series
        @param question_id_list: The list of questions to display
    """
    s3db = current.s3db
    db = current.db

    headers = []
    types = []
    items = []
    qstn_posn = 0
    rowLen = len(question_id_list)
    complete_lookup = {}
    for question_id in question_id_list:
        answers = survey_getAllAnswersForQuestionInSeries(question_id,
                                                   series_id)
        widgetObj = getWidgetFromQuestion(question_id)

        qtable = s3db.survey_question
        query = (qtable.id == question_id)
        question = db(query).select(qtable.name,
                                    limitby=(0, 1)).first()
        headers.append(question.name)
        types.append(widgetObj.db_type())

        for answer in answers:
            complete_id = answer["complete_id"]
            if complete_id in complete_lookup:
                row = complete_lookup[complete_id]
            else:
                row = len(complete_lookup)
                complete_lookup[complete_id]=row
                items.append(['']*rowLen)
            items[row][qstn_posn] = widgetObj.repr(answer["value"])
        qstn_posn += 1
    return [headers] + [types] + items

def getLocationList(series_id):
    s3db = current.s3db
    db = current.db

    comtable = s3db.survey_complete
    query = db(comtable.series_id == series_id)
    rows = query.select(comtable.id)
    response_locations = []
    for row in rows:
        locWidget = get_default_location(row.id)
        complete_id = locWidget.question["complete_id"]
        if "answer" not in locWidget.question:
            continue
        answer = locWidget.question["answer"]
        if locWidget != None:
            record = locWidget.getLocationRecord(complete_id, answer)
            if len(record.records) == 1:
                location = record.records[0].gis_location
                location.complete_id = complete_id
                response_locations.append(location)
    return response_locations


class S3TranslateModel(S3Model):
    """
        Translate Model
    """
    from gluon.languages import read_dict, write_dict

    names = ["survey_translate"]

    def model(self):

        db = current.db
        T = current.T
        s3 = current.response.s3

        """
            The survey_translate table holds the details of the language
            for which the template has been translated into.
        """
        tablename = "survey_translate"
        template_id = self.survey_template_id
        LANG_HELP = T("This is the full name of the language and will be displayed to the user when selecting the template language.")
        CODE_HELP = T("This is the short code of the language and will be used as the name of the file. This should be the ISO 639 code.")
        table = self.define_table(tablename,
                                template_id(),
                                Field("language",
                                       readable=True,
                                       writable=True,
                                       comment = DIV(_class="tooltip",
                                                     _title="%s|%s" % (T("Language"),
                                                            LANG_HELP))
                                       ),
                                Field("code",
                                       readable=True,
                                       writable=True,
                                       comment = DIV(_class="tooltip",
                                                     _title="%s|%s" % (T("Language Code"),
                                                            CODE_HELP))
                                       ),
                                Field("file",
                                      "upload",
                                      autodelete=True),
                                Field("filename",
                                      readable=False,
                                      writable=False),
                                *s3.meta_fields())
        s3.crud_strings[tablename] = Storage(
            title_create = T("Add new translation language"),
        )

        self.configure(tablename,
                       onaccept = self.translate_onaccept,
                      )
        # ---------------------------------------------------------------------
        return Storage()


    @staticmethod
    def translate_onaccept(form):
        """
            If the translation spreadsheet has been uploaded then
            it needs to be processed.

            The translation strings need to be extracted from
            the spreadsheet and inserted into the language file.
        """
        T = current.T
        request =  current.request
        response = current.response

        if "file" in form.vars:
            try:
                import xlrd
            except ImportError:
                print >> sys.stderr, "ERROR: xlrd & xlwt modules are needed for importing spreadsheets"
                return None

            from gluon.languages import read_dict, write_dict

            msgNone = T("No translations exist in spreadsheet")
            upload_file = request.post_vars.file
            upload_file.file.seek(0)
            openFile = upload_file.file.read()
            lang = form.record.language
            code = form.record.code
            try:
                workbook = xlrd.open_workbook(file_contents=openFile)
            except:
                msg = T("Unable to open spreadsheet")
                response.error = msg
                response.flash = None
                return
            try:
                sheetL = workbook.sheet_by_name(lang)
            except:
                msg = T("Unable to find sheet %(sheet_name)s in uploaded spreadsheet") % \
                    dict(sheet_name=lang)
                response.error = msg
                response.flash = None
                return
            if sheetL.ncols == 1:
                response.warning = msgNone
                response.flash = None
                return
            count = 0
            lang_fileName = "applications/%s/uploads/survey/translations/%s.py" % \
                (request.application, code)
            try:
                strings = read_dict(lang_fileName)
            except:
                strings = dict()
            for row in xrange(1, sheetL.nrows):
                original = sheetL.cell_value(row, 0)
                translation = sheetL.cell_value(row, 1)
                if (original not in strings) or translation != "":
                    strings[original] = translation
                    count += 1
            write_dict(lang_fileName, strings)
            if count == 0:
                response.warning = msgNone
                response.flash = None
            else:
                response.flash = T("%(count_of)d translations have been imported to the %(language)s language file") % \
                    dict(count_of=count, language=lang)


def survey_getTranslation(translation_id):
    """
        Return the template translation record for the id passed in
    """
    s3db = current.s3db
    db = current.db

    table = s3db.survey_translate
    query = (table.id == translation_id)
    return db(query).select(limitby=(0, 1)).first()

def survey_getAllTranslationsForTemplate(template_id):
    """
        function to return all the translations for the given template
    """
    s3db = current.s3db
    db = current.db

    table = s3db.survey_translate
    query = (table.template_id == template_id)
    row = db(query).select()
    return row

def survey_getAllTranslationsForSeries(series_id):
    """
        function to return all the translations for the given series
    """
    row = survey_getSeries(series_id)
    template_id = row.template_id
    return survey_getAllTranslationsForTemplate(template_id)



# Generic function called by the duplicator methods to determine if the
# record already exists on the database.
def duplicator(job, query):
    """
      This callback will be called when importing records it will look
      to see if the record being imported is a duplicate.

      @param job: An S3ImportJob object which includes all the details
                  of the record being imported

      If the record is a duplicate then it will set the job method to update
    """
    # ignore this processing if the id is set
    if job.id:
        return

    db = current.db

    table = job.table
    _duplicate = db(query).select(table.id, limitby=(0, 1)).first()
    if _duplicate:
        job.id = _duplicate.id
        job.data.id = _duplicate.id
        job.method = job.METHOD.UPDATE


# END =========================================================================