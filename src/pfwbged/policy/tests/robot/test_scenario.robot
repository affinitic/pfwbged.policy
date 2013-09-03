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
#    Capture viewport screenshot  ${SSDIR}/parametrage/envoi-courriel.png
#    Capture page screenshot  ${SSDIR}/parametrage/envoi-courriel.png
    Click Button  form.actions.save

Log in as
    [Arguments]     ${username}
    Log in  ${username}  secret

Open supermenu
    # Open menu  Workfplone-contentmenu-workflow
    Open Workflow Menu

Go to documents
    Go to  ${PLONE_URL}/documents

State should be
    [Arguments]  ${state}
    Element should contain  id=formfield-form-widgets-review_state  ${state}

Enter deadline
    ${yyyy}  ${mm}  ${dd} =  Get Time  year,month,day
    Input Text  form-widgets-IDeadline-deadline-year   ${yyyy}
    Select From List  form-widgets-IDeadline-deadline-month  ${mm}
    Input Text  form-widgets-IDeadline-deadline-day    ${dd}
    Input Text  form-widgets-IDeadline-deadline-hour    18
    Input Text  form-widgets-IDeadline-deadline-minute    00

Enter date
    [Arguments]     ${field_name}
    ${yyyy}  ${mm}  ${dd} =  Get Time  year,month,day
    Input Text  ${field_name}-year   ${yyyy}
    Select From List  ${field_name}-month  ${mm}
    Input Text  ${field_name}-day    ${dd}

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

Overlay should close
    Element should not remain visible  id=exposeMask
    Wait until keyword succeeds  60  1  Page should not contain element  css=div.overlay

Overlay is opened
    Wait Until Page Contains Element  css=.overlay

Add incoming mail
    [Arguments]    ${title}  ${sender}
    Go to documents
    Open supermenu
    Click link  id=dmsincomingmail
    Wait Until Page Contains Element  id=form-widgets-IDublinCore-title
    Input Text    form-widgets-IDublinCore-title  ${title}
    Select contact  ${sender}
    Wait Until Page Contains Element  id=form-widgets-IDeadline-deadline-year
    Enter deadline
    Input Text  form-widgets-reception_date-hour    18
    Input Text  form-widgets-reception_date-minute    00
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
    [Documentation]  Ouvrir la lettre et scanner le courrier
    Log in as  secretaire
    Add incoming mail  New mail  Général
    Click link  Modifier
    [Documentation]  Indicatage et encodage de l’attribution du courrier
    # Select chef_info for treating_groups
    Focus  css=#form_widgets_IPfwbIncomingMail_treated_by_select_chzn input
    Click element  id=form_widgets_IPfwbIncomingMail_treated_by_select_chzn_o_4
    # Select chef_finances for treating_groups
    Focus  css=#form_widgets_IPfwbIncomingMail_in_copy_select_chzn input
    Click element  id=form_widgets_IPfwbIncomingMail_in_copy_select_chzn_o_3
    Select date in calendar  formfield-form-widgets-original_mail_date  5
    Select date in calendar  formfield-form-widgets-reception_date  8
    Save form
    Wait Until Page Contains  New mail
    [Documentation]  Mail is indicated
    Execute transition  to_assign
    State should be  À attribuer

    [Documentation]  Greffier assigns mail
    Log in as  greffier
    Go to  ${PLONE_URL}/documents/new-mail
    Execute transition  to_process
    State should be  En cours de traitement

    [Documentation]  Finances group member sees document
    Log in as  finances
    Go to documents
    Element Should Be Visible  id=folder-contents-item-new-mail

    [Documentation]  info group member sees document
    Log in as  info
    Go to documents
    Element Should Be Visible  id=folder-contents-item-new-mail

    [Documentation]  Christine attributes task to Robert
    Log in as  christine
    Open favorite  task-responsible
    Click link  css=#searchresults a[href$='new-mail']
    Wait Until Page Contains  New mail
    Execute transition  attribute
    Overlay is opened
    Focus  css=#form_widgets_responsible_select_chzn input
    Input text  css=#form_widgets_responsible_select_chzn input  robert
    Wait Until Page Contains Element  css=.chzn-results
    Wait Until Page Contains  Robert
    Click element  id=form_widgets_responsible_select_chzn_o_0
    Input text  form-widgets-note  Merci de préparer une réponse négative au courrier pour cause d’irrecevabilité
    Save form
    Overlay should close
    Element should contain  css=table.listing  Christine
    Element should contain  css=table.listing  Robert

    [Documentation]  Robert takes document in charge
    Log in as  robert
    Open favorite  task-responsible
    Click link  css=#searchresults a[href$='new-mail']
    Wait Until Page Contains  New mail
    Execute transition  take-responsibility
    State should be  En cours de traitement
    # Create response
    Execute action  plone-contentmenu-actions-create_outgoing_mail
    Overlay is opened
    Save form
    Overlay should close
    Title is  Re: New mail
    Element should contain  css=.documentAuthor  Robert

    # Colleague doesn't see outgoing mail
    Log in as  info
    Go to documents
    Page should not contain  Re: New mail

    Log in as  christine
    Open favorite  task-responsible
    Element should contain  css=table.listing tbody tr:nth-child(1)  Attribu
    Open favorite  task-enquirer
    Element should contain  css=table.listing tbody tr:nth-child(1)  En cours

    Log in as  greffier
    Open favorite  task-enquirer
    Element should contain  css=table.listing tbody tr:nth-child(1)  Attribu

    [Documentation]  Création d’une première version de réponse
    Log in as  robert
    Go to documents
    Click link  css=.listing a[href$='documents/new-mail']
    Wait Until Page Contains  New mail
    Click link  css=#formfield-form-widgets-related_docs a[href$='re-new-mail']
    Wait Until Page Contains  Re: New mail

    Create version  1  Robert

    [Documentation]  Demande d’avis à un collègue
    Ask opinion to  abd  Abdes  Peux-tu me dire ce que tu penses de la rédaction de la justification de refus ?  1

    [Documentation]  Remise d’un avis
    Log in as  abdes
    Open favorite  opinion-responsible
    Click link  css=#searchresults a[href$='re-new-mail']
    Title is  Re: New mail
    Click link  css=.listing a[href$='demande-davis-pour-la-version-1']
    Overlay is opened
    Input text  form-widgets-comment-text  Je serais plus direct, du genre : vous ne respectez pas les conditions de subside
    Click button  form-buttons-render_opinion
    Overlay should close
    ## Element should contain  css=.listing tbody  Fait  # [bug] sélecteur pas assez précis
    Page should contain  Fait
    State should be  En rédaction

    [Documentation]  Nouvelle version suite à l’avis rendu
    Log in as  robert
    Open favorite  opinion-enquirer
    Click link  css=#searchresults a[href$='re-new-mail']
    Wait Until Page Contains  Re: New mail
    Create version  2  Robert

    # Abdes doesn't see version 2
    Log in as  abdes
    Go to documents
    Click link  css=.listing a[href$='documents/re-new-mail']
    Wait Until Page Contains  Re: New mail
    #Versions should not contain  2

    [Documentation]  Demande de validation
    Log in as  robert
    Go to documents
    Click link  css=.listing a[href$='documents/re-new-mail']
    Wait Until Page Contains  Re: New mail
    Ask validation to  chri  Christine  2
    Page should contain  Demande de validation pour la version 2
    Versions should contain  En cours de validation

    [Documentation]  Validation
    Log in as  christine
    Open favorite  validation-responsible
    Click link  css=#searchresults a[href$='re-new-mail']
    Wait Until Page Contains  Re: New mail
    #Versions should not contain  1
    Execute transition on version  validate  2
    Wait Until Page Contains  Validé

    [Documentation]  Demande de validation au « greffier »
    Ask validation to  greff  Greffier  2
    Page should contain  Greffier
    Versions should contain  En cours de validation


    [Documentation]  Refus de validation avec commentaire
    Log in as  greffier
    Open favorite  validation-responsible
    Click link  css=#searchresults a[href$='re-new-mail']
    Wait Until Page Contains  Re: New mail
    # [bug] Greffier ne doit pas voir version 1 mais il la voit
    ### Versions should not contain  1
    Execute transition on version  refuse  2
    Element should contain  css=.listing  En rédaction
    Page should contain  Refus
    Click link  css=.listing a[href$='demande-de-validation-pour-la-version-2-1']
    Overlay is opened
    Input text  form-widgets-comment-text  Merci d'expliquer la règle applicable et de me soumettre une version corrigée
    Click button  form-buttons-comment
    Overlay should close

    [Documentation]  Nouvelle version suite au refus de validation
    Log in as  christine
    Open favorite  validation-enquirer
    Element should contain  css=table.listing tbody  Refus
    Click link  css=#searchresults a[href$='re-new-mail']
    Wait Until Page Contains  Re: New mail
    Create version  3  Christine

    [Documentation]  Nouvelle demande de validation
    Ask validation to  greff  Greffier  3
    Versions should contain  En cours de validation
    Page should not contain  Modifier

    [Documentation]  Validation
    Log in as  greffier
    Open favorite  validation-responsible
    Click link  css=#searchresults a[href$='re-new-mail']
    Wait Until Page Contains  Re: New mail
    Page should contain  Modifier
    Execute transition on version  validate  3
    Page should contain  Validé

    # [bug]  Partage de version ?  -> ça n'existe pas !
    # Robert don't see version 3
    Log in as  robert
    Go to documents
    Click link  css=.listing a[href$='documents/re-new-mail']
    Wait Until Page Contains  Re: New mail
    Versions should contain  1
    Versions should contain  2
    #Versions should not contain  3

    [Documentation]  Finalisation de la version
    Log in as  christine
    Go to documents
    Click link  css=.listing a[href$='documents/re-new-mail']
    Wait Until Page Contains  Re: New mail
    Versions should contain  Valid
    Execute transition on version  finish  3
    Page should contain  Prêt à être envoyé
    Versions should contain  Finalisé
    Versions should contain  Obsolète

    [Documentation]  Import de la version signée.
    Log in as  greffier
    Go to documents
    Click link  css=.listing a[href$='documents/re-new-mail']
    Select version  3
    Execute action  plone-contentmenu-actions-create_signed_version
    Overlay is opened
    Wait for condition  return $('.overlay #form-widgets-signed-0').length
    Checkbox Should Be Selected  css=.overlay #form-widgets-signed-0
    Choose File  form-widgets-file-input  ${tests_path}/document-test.odt
    Save form
    Overlay should close
    Versions should contain  Version signée

    Click link  css=#formfield-form-widgets-in_reply_to a
    Wait Until Page Contains  chef_info
    Page Should Contain  En cours de traitement

    Log in as  robert
    Go to documents
    Click link  css=.listing a[href$='documents/re-new-mail']
    Wait Until Page Contains  Version signée
    Execute transition  send
    Wait Until Page Contains  Envoyé

    Click link  css=#formfield-form-widgets-in_reply_to a
    Wait Until Page Contains  chef_info
    Page should contain  Répondu
