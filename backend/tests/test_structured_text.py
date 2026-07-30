from PIL import Image
from openpyxl import Workbook, load_workbook

from backend.converters.excel_to_pdf import ExcelToPdfConverter
from backend.converters.html_to_pdf import HtmlToPdfConverter
from backend.converters.excel_to_html import ExcelToHtmlConverter
from backend.converters.json_to_html import JsonToHtmlConverter
from backend.converters.json_to_svg import JsonToSvgConverter
from backend.converters.pdf_to_image import PdfToImageConverter
from backend.converters.xml_to_html import XmlToHtmlConverter
from backend.converters.xml_to_svg import XmlToSvgConverter
from backend.converters.xml_to_txt import XmlToTxtConverter
from backend.utils.structured_text import extract_json_texts, extract_xml_texts


def test_extract_xml_texts_returns_content_without_element_names():
    from xml.etree import ElementTree as ET

    root = ET.fromstring('<document><title>标题</title><para>第一段</para><para>第二段</para></document>')

    assert extract_xml_texts(root) == ['标题', '第一段', '第二段']


def test_extract_json_texts_returns_string_values_only():
    data = {'title': '标题', 'meta': {'node_type': 'paragraph', 'content': '正文'}, 'items': ['第一项']}

    assert extract_json_texts(data) == ['标题', '正文', '第一项']


def test_nearly_blank_page_is_ignored():
    image = Image.new('RGB', (1000, 1000), 'white')
    image.putpixel((500, 500), (245, 245, 245))

    assert PdfToImageConverter()._is_image_empty(image)


def test_excel_page_settings_honor_user_selection():
    settings = ExcelToPdfConverter()._resolve_page_settings(
        {'page_size': 'A3', 'excel_orientation': 'landscape', 'excel_scale_mode': 'fit_width'},
        col_count=3,
    )

    assert settings == {'paper_size': 8, 'orientation': 2, 'scale_mode': 'fit_width'}


def test_excel_page_settings_preserve_wide_sheet_auto_scale():
    settings = ExcelToPdfConverter()._resolve_page_settings({}, col_count=20)

    assert settings == {'paper_size': 8, 'orientation': 2, 'scale_mode': 'scaled_85'}


def test_libreoffice_workbook_contains_requested_print_settings(tmp_path):
    source = tmp_path / 'source.xlsx'
    prepared = tmp_path / 'prepared.xlsx'
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(['Name', 'January', 'February'])
    worksheet.append(['Item', 10, 20])
    workbook.save(source)
    workbook.close()

    ExcelToPdfConverter()._prepare_libreoffice_workbook(
        str(source),
        str(prepared),
        {
            'page_size': 'A4',
            'excel_orientation': 'landscape',
            'excel_scale_mode': 'fit_width',
        },
    )

    prepared_workbook = load_workbook(prepared)
    try:
        prepared_sheet = prepared_workbook.active
        assert prepared_sheet.page_setup.paperSize == 9
        assert prepared_sheet.page_setup.orientation == 'landscape'
        assert prepared_sheet.page_setup.fitToWidth == 1
        assert prepared_sheet.page_setup.fitToHeight == 0
        assert prepared_sheet.sheet_properties.pageSetUpPr.fitToPage is True
    finally:
        prepared_workbook.close()


def test_xml_display_exports_keep_text_and_remove_source_tags(tmp_path):
    source = tmp_path / 'sample.xml'
    source.write_text(
        '<document><title>转换标题</title><para>第一段正文</para><para>第二段正文</para></document>',
        encoding='utf-8',
    )

    outputs = {
        'html': (XmlToHtmlConverter(), tmp_path / 'sample.html'),
        'txt': (XmlToTxtConverter(), tmp_path / 'sample.txt'),
        'svg': (XmlToSvgConverter(), tmp_path / 'sample.svg'),
    }
    for converter, output in outputs.values():
        assert converter.convert(str(source), str(output))['success']
        content = output.read_text(encoding='utf-8')
        assert '第一段正文' in content
        assert '第二段正文' in content
        assert '&lt;para&gt;' not in content
        assert '<para>' not in content


def test_json_display_exports_keep_text_and_remove_json_syntax(tmp_path):
    source = tmp_path / 'sample.json'
    source.write_text(
        '{"title":"转换标题","node_type":"paragraph","content":"正文内容"}',
        encoding='utf-8',
    )

    outputs = {
        'html': (JsonToHtmlConverter(), tmp_path / 'sample.html'),
        'svg': (JsonToSvgConverter(), tmp_path / 'sample.svg'),
    }
    for converter, output in outputs.values():
        assert converter.convert(str(source), str(output))['success']
        content = output.read_text(encoding='utf-8')
        assert '转换标题' in content
        assert '正文内容' in content
        assert 'node_type' not in content
        assert '&quot;content&quot;' not in content


def test_html_print_blank_tail_page_is_not_exported(tmp_path):
    source = tmp_path / 'sample.html'
    pdf_output = tmp_path / 'sample.pdf'
    image_output = tmp_path / 'sample.png'
    source.write_text(
        '<!doctype html><meta charset="utf-8"><p>有效正文</p>'
        '<div style="break-before: page; page-break-before: always"></div>',
        encoding='utf-8',
    )

    assert HtmlToPdfConverter().convert(str(source), str(pdf_output))['success']
    result = PdfToImageConverter().convert(str(pdf_output), str(image_output), merge=True)

    assert result['success']
    assert result['page_count'] == 1


def test_html_page_options_are_added_to_browser_print_css():
    html = HtmlToPdfConverter()._prepare_html_content(
        '<html><head></head><body>正文</body></html>',
        {'page_size': 'A3', 'orientation': 'landscape'},
    )

    assert '@page { size: A3 landscape; margin: 10mm; }' in html


def test_excel_html_fit_width_uses_wrapped_full_width_table(tmp_path):
    from openpyxl import Workbook

    source = tmp_path / 'sample.xlsx'
    output = tmp_path / 'sample.html'
    workbook = Workbook()
    workbook.active.append(['第一列', '第二列'])
    workbook.save(source)

    result = ExcelToHtmlConverter().convert(
        str(source),
        str(output),
        excel_scale_mode='fit_width',
    )
    content = output.read_text(encoding='utf-8')

    assert result['success']
    assert 'width: 100%' in content
    assert 'overflow-wrap: anywhere' in content
