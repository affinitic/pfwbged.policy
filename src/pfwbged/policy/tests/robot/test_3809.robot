*** Settings ***

Resource  plone/app/robotframework/keywords.robot
#Resource  annotate.robot
#Resource  keywords.robot


Library  Remote  ${PLONE_URL}/RobotRemote

Test Setup  Run keywords  Open test browser  Setup Plone site
Test Teardown  Close all browsers

*** Variables ***
${tests_path}  /home/vincentfretin/workspace/pfwbged.buildout/src/pfwbged.policy/src/pfwbged/policy/tests
#${tests_path}  /home/cedricmessiant/workspace/buildouts/pfwbged.buildout/src/pfwbged.policy/src/pfwbged/policy/tests

*** Keywords ***
Setup Plone site
    Given a site owner
      and a French Plone site
      and mail configured
    Disable autologin

Save form
    Wait until page contains element  form-buttons-save
    Click button  form-buttons-save

Title is
    [Arguments]   ${title}
    Wait Until Page Contains  ${title}
    Element should contain  css=h1.documentFirstHeading  ${title}

a site owner
    Enable autologin as  Manager
    Set autologin username  admin

a French Plone site
    Go to  ${PLONE_URL}/@@language-controlpanel
    Select From List  form.default_language  fr
    Click Button  form.actions.save

mail configured
    Go to  ${PLONE_URL}/@@mail-controlpanel
    Input text  name=form.smtp_host  smtp.monfai.fr
    Input text  name=form.smtp_port  25
    Input text  name=form.email_from_name  Webmestre de Plone.fr
    Input text  name=form.email_from_address  webmestre@plone.fr
    Click Button  form.actions.save

Log in as
    [Arguments]     ${username}
    Log in  ${username}  secret

Open supermenu
    Open Workflow Menu

Go to documents
    Go to  ${PLONE_URL}/documents

State should be
    [Arguments]  ${state}
    Element should contain  id=formfield-form-widgets-review_state  ${state}

Verify date
    [Arguments]     ${field_name}  ${yyyy}  ${mm}  ${dd}  ${hour}=18  ${minute}=00
    Textfield Value Should Be  ${field_name}-year  ${yyyy}
    ${month}  Get Selected List Value  ${field_name}-month
    Should Be Equal As Integers  ${mm}  ${month}
    # transform '04' to '4'
    ${day} =  Convert To Integer  ${dd}
    ${day} =  Convert To String  ${day}
    Textfield Value Should Be  ${field_name}-day  ${day}
    Textfield Value Should Be  ${field_name}-hour  ${hour}
    Textfield Value Should Be  ${field_name}-minute  ${minute}

Enter date
    [Arguments]     ${field_name}  ${yyyy}  ${mm}  ${dd}  ${hour}=18  ${minute}=00
#    ${yyyy}  ${mm}  ${dd} =  Get Time  year,month,day
    ${day} =  Convert To Integer  ${dd}
    ${day} =  Convert To String  ${day}
    ${month} =  Convert To Integer  ${mm}
    ${month} =  Convert To String  ${month}
    Input Text  ${field_name}-year  ${yyyy}
    Select From List  ${field_name}-month  ${month}
    Input Text  ${field_name}-day  ${day}
    Input Text  ${field_name}-hour  ${hour}
    Input Text  ${field_name}-minute  ${minute}

Select date in calendar
    [Arguments]    ${field}  ${dd}
    Click element  css=#${field} .caltrigger
    Element Should Be Visible  id=calroot
    Click Element  xpath=//a[@href='#${dd}']

Select contact
    [Arguments]    ${contact}
    Input Text    form.widgets.sender.widgets.query      ${contact}
    Click element  form.widgets.sender.widgets.query
    Wait Until Page Contains Element  css=.ac_results
    Click element  css=.ac_results li:nth-child(1)

Execute transition
    [Arguments]    ${transition}
    Open supermenu
    Element should become visible  css=#contentActionMenus a#workflow-transition-${transition}
    Click element  css=#contentActionMenus a#workflow-transition-${transition}

Execute transition on version
    [Arguments]    ${transition}  ${version}
    Select version  ${version}
    Open supermenu
    Element should become visible  css=#contentActionMenus a.version-id-${version}#workflow-transition-${transition}
    Click element  css=#contentActionMenus a.version-id-${version}#workflow-transition-${transition}

Execute action
    [Arguments]    ${action_name}
    Open supermenu
    Element should become visible  id=${action_name}
    Click element  id=${action_name}

Open favorite
    [Arguments]    ${name}
    Click element  css=#portal-down .open
    Element should become visible  id=favorites
    Click element  css=#favorites a[href$='${name}']
    Wait Until Page Contains Element  id=searchresults

Close Overlay
    Click Element  css=div.overlay div.close

Overlay should close
    Element should not remain visible  id=exposeMask
    Wait until keyword succeeds  60  1  Page should not contain element  css=div.overlay

Overlay is opened
    Wait Until Page Contains Element  css=.overlay

Add board decision
    [Arguments]    ${title}
    Go to documents
    Open supermenu
    Capture Page Screenshot  /tmp/t.png
    Click link  id=pfwb-boarddecision
    Wait Until Page Contains Element  id=form-widgets-IBasic-title
    Input Text    form-widgets-IBasic-title  ${title}
    Save form
    Title is  ${title}

Add incoming mail
    [Arguments]    ${title}  ${sender}
    Go to documents
    Open supermenu
    Click link  id=dmsincomingmail
    Wait Until Page Contains Element  id=form-widgets-IBasic-title
    Input Text    form-widgets-IBasic-title  ${title}
    Select contact  ${sender}
    Wait Until Page Contains Element  id=form-widgets-IDeadline-deadline-year

    ${yyyy}  ${mm}  ${dd} =  Get Time  year,month,day
    Verify date  form-widgets-reception_date  ${yyyy}  ${mm}  ${dd}  18

    # ideally we would check the deadline but this would require proper date
    # manipulation code, the following code is too naive:
    #  ${day} =  Convert To Integer  ${dd}
    #  ${day} =  Evaluate  ${day} + 3
    #  ${day} =  Convert To String  ${day}
    #  Verify date  form-widgets-IDeadline-deadline  ${yyyy}  ${mm}  ${day}  12

    # change reception date just to test it
    Enter date  form-widgets-reception_date  2013  03  04  10  00
    Verify date  form-widgets-reception_date  2013  03  04  10  00
    Save form
    Title is  ${title}

Create version
    [Arguments]  ${version_number}  ${creator}
    Execute action  dmsmainfile
    Choose File  form-widgets-file-input  ${tests_path}/document-test.odt
    Save form
    Overlay should close
    # Version is created
    Wait until page contains element  css=#fieldset-versions .listing
    Versions should contain  ${version_number}
    Versions should contain  ${creator}
    Page should contain element  id=DV-container

Ask opinion to
    [Arguments]  ${short}  ${responsible}  ${note}  ${version}
    Execute transition on version  ask_opinion  ${version}
    Focus  css=#form_widgets_responsible_select_chzn input
    Input text  css=#form_widgets_responsible_select_chzn input  ${short}
    Wait Until Page Contains Element  css=.chzn-results
    Wait for condition  return ($('#form_widgets_responsible_select_chzn_o_0').text().indexOf('${responsible}') != -1)
    Click element  id=form_widgets_responsible_select_chzn_o_0
    Input text  form-widgets-note  ${note}
    Save form
    Overlay should close

Ask validation to
    [Arguments]  ${short}  ${responsible}  ${version}
    #  ${note}  # [bug] en faire un argument optionnel ?
    Execute transition on version  submit  ${version}
    Focus  css=#form_widgets_responsible_select_chzn input
    Input text  css=#form_widgets_responsible_select_chzn input  ${short}
    Wait Until Page Contains Element  css=.chzn-results
    Wait for condition  return ($('#form_widgets_responsible_select_chzn_o_0').text().indexOf('${responsible}') != -1)
    Click element  id=form_widgets_responsible_select_chzn_o_0
    #Input text  form-widgets-note  ${note}
    Save form
    Overlay should close

Versions should contain
    [Arguments]  ${text}
    Element should contain  css=#fieldset-versions .listing    ${text}

Versions should not contain
    [Arguments]  ${text}
    #[bug]  Element should not contain n'existe pas !
    #Element should not contain  css=#fieldset-versions .listing  ${text}

Select version
    [Arguments]  ${version_id}
    Click element  css=#fieldset-versions a.version-link[href$='${version_id}']
    Wait For Condition  return $("#fieldset-versions a.version-link[href$=${version_id}]").closest('tr').hasClass('selected')

*** Test cases ***

Scenario
    [Documentation]  Créer une décision du bureau
    Log in as  secretaire
    Add board decision  Decision 3809
    Go to documents
    Page Should Contain  Decision 3809

    Log in as  reader
    Go to documents
    Page Should Not Contain  Decision 3809

    [Documentation]  Ajouter une version
    Log in as  secretaire
    Go to documents
    Click link  css=a[href$='decision-3809']
    Create version  1  Secretaire

    [Documentation]  Vérifier que la décision avec une version reste inaccessible pour un lecteur
    Log in as  reader
    Go to documents
    Page Should Not Contain  Decision 3809

    [Documentation]  Finir sans validation
    Log in as  secretaire
    Go to documents
    Click link  css=a[href$='decision-3809']
    Execute transition  finish_without_validation
    Go to documents

    [Documentation]  Vérifier que la décision finalisée reste inaccessible pour un lecteur
    Log in as  reader
    Go to documents
    Page Should Not Contain  Decision 3809
