<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:src="http://nwalsh.com/xmlns/litprog/fragment"
  exclude-result-prefixes="src" version="1.0">

<!-- THIS XSL IS FOR GENERATING FO OUTPUT -->

<!-- Include the default settings -->
  <xsl:import href="/usr/share/xml/docbook/stylesheet/nwalsh/fo/docbook.xsl"/>

  <xsl:param name="draft.mode" select="'no'"/>
  <xsl:param name="paper.type" select="'A4'"/>
  <xsl:param name="fop.extensions" select="1"/>
  <xsl:param name="chapter.autolabel" select="1"></xsl:param>
  <xsl:param name="appendix.autolabel" select="1"></xsl:param>
  <xsl:param name="section.autolabel" select="1"></xsl:param>
  <xsl:param name="section.autolabel.max.depth" select="3"></xsl:param>

  <xsl:param name="shade.verbatim" select="1"></xsl:param>

<!-- use this to select the image type used for pdf / ps output across all files. -->
  <xsl:param name="graphic.default.extension" select="'gif'"></xsl:param>

  <xsl:param name="hyphenate.verbatim" select="0"></xsl:param>

<xsl:attribute-set name="monospace.verbatim.properties"
		   use-attribute-sets="verbatim.properties">
  <xsl:attribute name="wrap-option">wrap</xsl:attribute>
  <xsl:attribute name="hyphenation-character">\</xsl:attribute>
  <xsl:attribute name="font-size">11pt</xsl:attribute>
</xsl:attribute-set>

  <xsl:param name="monospace.font.family" select="'Times'"/>

  <xsl:param name="body.font.master" select="12" />

<!--   <xsl:param name="linenumbering.extension" select="0"></xsl:param> -->
<!--   <xsl:param name="use.extensions" select="1"></xsl:param> -->



</xsl:stylesheet>