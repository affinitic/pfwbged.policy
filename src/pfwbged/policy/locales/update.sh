domain=pfwbged.policy
i18ndude rebuild-pot --pot $domain.pot --merge $domain-manual.pot --create $domain ../
i18ndude sync --pot $domain.pot */LC_MESSAGES/$domain.po

i18ndude rebuild-pot --pot plone.pot --merge plone-manual.pot --create plone ../profiles               
i18ndude sync --pot plone.pot */*/plone.po
