import zipfile
from pathlib import Path

import fitz
from docx import Document
from openpyxl import Workbook
from PIL import Image, ImageChops, ImageStat

from backend.converters.docx_to_image import DocxToImageConverter
from backend.converters.excel_to_pdf import ExcelToPdfConverter
from backend.converters.excel_to_ppt import ExcelToPptConverter
from backend.converters.html_to_gif import HtmlToGifConverter
from backend.converters.html_to_image import HtmlToImageConverter
from backend.converters.html_to_pdf import HtmlToPdfConverter
from backend.converters.html_to_svg import HtmlToSvgConverter
from backend.converters.json_to_html import JsonToHtmlConverter
from backend.converters.json_to_image import JsonToImageConverter
from backend.converters.json_to_pdf import JsonToPdfConverter
from backend.converters.json_to_svg import JsonToSvgConverter
from backend.converters.pdf_to_md import PdfToMdConverter
from backend.converters.pdf_to_ppt import PdfToPptConverter
from backend.converters.txt_to_image import TxtToImageConverter
from backend.converters.txt_to_speech import TxtToSpeechConverter
from backend.converters.xml_to_html import XmlToHtmlConverter
from backend.converters.xml_to_image import XmlToImageConverter
from backend.converters.xml_to_pdf import XmlToPdfConverter
from backend.converters.xml_to_svg import XmlToSvgConverter
from backend.utils.text_utils import detect_tts_language


def _assert_image_has_content(path: Path) -> Image.Image:
    image = Image.open(path).convert('RGB')
    background = Image.new('RGB', image.size, image.getpixel((0, 0)))
    difference = ImageChops.difference(image, background).convert('L')
    assert ImageStat.Stat(difference).extrema[0][1] > 20
    return image


def _assert_valid_pptx(path: Path, minimum_slides: int = 1) -> None:
    assert path.exists() and path.stat().st_size > 0
    with zipfile.ZipFile(path) as archive:
        slide_names = [
            name for name in archive.namelist()
            if name.startswith('ppt/slides/slide') and name.endswith('.xml')
        ]
        assert len(slide_names) >= minimum_slides


def _make_text_pdf(path: Path, text: str = 'Regression PDF content') -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def _make_docx(path: Path) -> None:
    document = Document()
    document.add_heading('Watermark regression', level=1)
    document.add_paragraph('DOCX image conversion content')
    document.save(path)


def _make_xlsx(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Regression'
    worksheet.append(['Name', 'January', 'February', 'March'])
    for index in range(1, 8):
        worksheet.append([f'Item {index}', index * 10, index * 20, index * 30])
    workbook.save(path)


def test_docx_png_and_jpg_apply_watermark(tmp_path):
    source = tmp_path / 'source.docx'
    _make_docx(source)
    converter = DocxToImageConverter()

    for extension in ('png', 'jpg'):
        plain = tmp_path / f'plain.{extension}'
        marked = tmp_path / f'marked.{extension}'
        converter.convert(str(source), str(plain), quality=90)
        converter.convert(
            str(source),
            str(marked),
            quality=90,
            watermark_text='Watermark 2026',
            watermark_opacity=90,
            watermark_size=44,
            watermark_color='#335577',
            watermark_angle=0,
            watermark_position='center',
        )

        plain_image = Image.open(plain).convert('RGB')
        marked_image = Image.open(marked).convert('RGB')
        assert plain_image.size == marked_image.size
        difference = ImageChops.difference(plain_image, marked_image).convert('L')
        assert ImageStat.Stat(difference).mean[0] > 0.05


def test_html_code_pdf_keeps_chinese_after_cleanup(tmp_path):
    source = tmp_path / 'source.html'
    output = tmp_path / 'source.pdf'
    source.write_bytes(
        '<html><head><meta charset="gb18030"><style>p{color:red}</style></head>'
        '<body><p>中文内容正常显示</p><script>window.bad=true</script></body></html>'.encode('gb18030')
    )

    result = HtmlToPdfConverter().convert(
        str(source),
        str(output),
        code_mode=True,
        encoding='gb18030',
        css_handling='remove',
        remove_scripts=True,
    )

    assert result['success']
    with fitz.open(output) as document:
        text = ''.join(page.get_text() for page in document)
    assert '中文内容正常显示' in text
    assert 'window.bad' not in text


def test_html_svg_and_image_formats_generate_valid_outputs(tmp_path):
    source = tmp_path / 'source.html'
    source.write_text(
        '<!doctype html><meta charset="utf-8"><h1>转换标题</h1><p>中文正文内容</p>',
        encoding='utf-8',
    )

    svg = tmp_path / 'output.svg'
    assert HtmlToSvgConverter().convert(str(source), str(svg))['success']
    svg_text = svg.read_text(encoding='utf-8')
    assert '<svg' in svg_text and ('中文正文内容' in svg_text or 'data:image/png;base64,' in svg_text)

    dimensions = []
    for extension, converter in (
        ('png', HtmlToImageConverter()),
        ('jpg', HtmlToImageConverter()),
        ('gif', HtmlToGifConverter()),
    ):
        output = tmp_path / f'output.{extension}'
        assert converter.convert(str(source), str(output))['success']
        image = _assert_image_has_content(output)
        dimensions.append(image.size)
    assert dimensions[0] == dimensions[1] == dimensions[2]


def test_pdf_markdown_and_powerpoint_outputs_are_usable(tmp_path):
    source = tmp_path / 'source.pdf'
    markdown = tmp_path / 'source.md'
    powerpoint = tmp_path / 'source.pptx'
    _make_text_pdf(source)

    md_result = PdfToMdConverter().convert(str(source), str(markdown))
    assert md_result['success']
    assert 'Regression PDF content' in markdown.read_text(encoding='utf-8')

    ppt_result = PdfToPptConverter().convert(str(source), str(powerpoint))
    assert ppt_result['success']
    _assert_valid_pptx(powerpoint)


def test_excel_powerpoint_and_landscape_pdf_outputs_are_usable(tmp_path):
    source = tmp_path / 'source.xlsx'
    _make_xlsx(source)
    powerpoint = tmp_path / 'source.pptx'
    pdf = tmp_path / 'source.pdf'

    ppt_result = ExcelToPptConverter().convert(str(source), str(powerpoint))
    assert ppt_result['success']
    _assert_valid_pptx(powerpoint)

    pdf_result = ExcelToPdfConverter().convert(
        str(source),
        str(pdf),
        page_size='A4',
        excel_orientation='landscape',
        excel_scale_mode='fit_width',
    )
    assert pdf_result['success']
    with fitz.open(pdf) as document:
        assert len(document) >= 1
        assert document[0].rect.width > document[0].rect.height


def test_txt_chinese_images_and_speech_language(tmp_path, monkeypatch):
    source = tmp_path / 'source.txt'
    source.write_text('这是中文语音和图片回归测试。', encoding='utf-8')

    for extension in ('png', 'jpg'):
        output = tmp_path / f'output.{extension}'
        assert TxtToImageConverter().convert(str(source), str(output))['success']
        _assert_image_has_content(output)

    assert detect_tts_language(source.read_text(encoding='utf-8')) == 'zh-CN'
    captured = {}

    def fake_gtts(self, text, output_path, language, rate, pitch):
        captured.update(text=text, language=language, rate=rate, pitch=pitch)
        Path(output_path).write_bytes(b'ID3-regression-audio')
        return {'success': True, 'output_path': output_path, 'method': 'test-gtts', 'language': language}

    monkeypatch.setattr(TxtToSpeechConverter, '_convert_with_gtts', fake_gtts)
    audio = tmp_path / 'output.mp3'
    result = TxtToSpeechConverter().convert(str(source), str(audio))
    assert result['success']
    assert captured['language'] == 'zh-CN'
    assert captured['text'].startswith('这是中文')


def test_xml_display_outputs_remove_tags_and_keep_all_text(tmp_path):
    source = tmp_path / 'source.xml'
    source.write_text(
        '<document><title>XML标题</title><para>第一段正文</para><para>第二段正文</para></document>',
        encoding='utf-8',
    )

    html_output = tmp_path / 'output.html'
    assert XmlToHtmlConverter().convert(str(source), str(html_output))['success']
    html_text = html_output.read_text(encoding='utf-8')
    assert '<para>' not in html_text and '&lt;para&gt;' not in html_text

    svg_output = tmp_path / 'output.svg'
    assert XmlToSvgConverter().convert(str(source), str(svg_output))['success']
    svg_text = svg_output.read_text(encoding='utf-8')
    assert '第一段正文' in svg_text and '第二段正文' in svg_text

    pdf_output = tmp_path / 'output.pdf'
    assert XmlToPdfConverter().convert(str(source), str(pdf_output))['success']
    with fitz.open(pdf_output) as document:
        pdf_text = ''.join(page.get_text() for page in document)
    assert '第一段正文' in pdf_text and '第二段正文' in pdf_text

    for extension in ('png', 'jpg'):
        image_output = tmp_path / f'output.{extension}'
        assert XmlToImageConverter().convert(str(source), str(image_output))['success']
        _assert_image_has_content(image_output)


def test_json_display_outputs_remove_structure_and_keep_text(tmp_path):
    source = tmp_path / 'source.json'
    source.write_text(
        '{"title":"JSON标题","node_type":"paragraph","content":"正文内容","items":["第一项","第二项"]}',
        encoding='utf-8',
    )

    html_output = tmp_path / 'output.html'
    assert JsonToHtmlConverter().convert(str(source), str(html_output))['success']
    html_text = html_output.read_text(encoding='utf-8')
    assert 'node_type' not in html_text and '&quot;content&quot;' not in html_text

    svg_output = tmp_path / 'output.svg'
    assert JsonToSvgConverter().convert(str(source), str(svg_output))['success']
    svg_text = svg_output.read_text(encoding='utf-8')
    assert '正文内容' in svg_text and 'node_type' not in svg_text

    pdf_output = tmp_path / 'output.pdf'
    assert JsonToPdfConverter().convert(str(source), str(pdf_output))['success']
    with fitz.open(pdf_output) as document:
        pdf_text = ''.join(page.get_text() for page in document)
    assert '正文内容' in pdf_text and 'node_type' not in pdf_text

    for extension in ('png', 'jpg'):
        image_output = tmp_path / f'output.{extension}'
        assert JsonToImageConverter().convert(str(source), str(image_output))['success']
        _assert_image_has_content(image_output)
