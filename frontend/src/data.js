import {
  FilePdfOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  CodeOutlined,
  FileTextOutlined
} from '@ant-design/icons';

export const categories = {
  'major_functions': [
    {
      name: 'docx_converter',
      icon: FileWordOutlined,
      description: 'docx_converter_desc',
      tools: [
        {
          name: 'DOCX To PDF',
          icon: FilePdfOutlined,
          description: 'Convert DOCX to PDF'
        },
        {
          name: 'DOCX To PNG',
          icon: FileWordOutlined,
          description: 'Convert DOCX to PNG'
        },
        {
          name: 'DOCX To JPG',
          icon: FileWordOutlined,
          description: 'Convert DOCX to JPG'
        },
        {
          name: 'DOCX To TXT',
          icon: FileWordOutlined,
          description: 'Convert DOCX to TXT'
        },
        {
          name: 'DOCX To EPUB',
          icon: FileWordOutlined,
          description: 'Convert DOCX to EPUB'
        },
        {
          name: 'DOCX To PPT',
          icon: FilePdfOutlined,
          description: 'Convert DOCX to PPT'
        }
      ]
    },
    {
      name: 'html_converter',
      icon: CodeOutlined,
      description: 'html_converter_desc',
      tools: [
        {
          name: 'HTML To PDF',
          icon: FilePdfOutlined,
          description: 'Convert HTML to PDF'
        },
        {
          name: 'HTML To JPG',
          icon: FileImageOutlined,
          description: 'Convert HTML to JPG'
        },
        {
          name: 'HTML To SVG',
          icon: FileImageOutlined,
          description: 'Convert HTML to SVG'
        },
        {
          name: 'HTML To GIF',
          icon: FileImageOutlined,
          description: 'Convert HTML to GIF'
        },
        {
          name: 'HTML To WORD',
          icon: FileWordOutlined,
          description: 'Convert HTML to WORD'
        },
        {
          name: 'HTML To PNG',
          icon: FileImageOutlined,
          description: 'Convert HTML to PNG'
        },
        {
          name: 'HTML To TEXT',
          icon: CodeOutlined,
          description: 'Convert HTML to TEXT'
        },
        {
          name: 'HTML To MD',
          icon: CodeOutlined,
          description: 'Convert HTML to MD'
        },
        {
          name: 'HTML To JSON',
          icon: CodeOutlined,
          description: 'Convert HTML to JSON'
        },
      ]
    },
    {
      name: 'json_converter',
      icon: CodeOutlined,
      description: 'json_converter_desc',
      tools: [
        {
          name: 'JSON To PDF',
          icon: FilePdfOutlined,
          description: 'Convert JSON to PDF'
        },
        {
          name: 'JSON To PNG',
          icon: FileImageOutlined,
          description: 'Convert JSON to PNG'
        },
        {
          name: 'JSON To JPG',
          icon: FileImageOutlined,
          description: 'Convert JSON to JPG'
        },
        {
          name: 'JSON To SVG',
          icon: FileImageOutlined,
          description: 'Convert JSON to SVG'
        },
        {
          name: 'JSON To CSV',
          icon: FileExcelOutlined,
          description: 'Convert JSON to CSV'
        },
        {
          name: 'JSON To HTML',
          icon: CodeOutlined,
          description: 'Convert JSON to HTML'
        },
        {
          name: 'JSON To YAML',
          icon: CodeOutlined,
          description: 'Convert JSON to YAML'
        },
        {
          name: 'JSON To XML',
          icon: CodeOutlined,
          description: 'Convert JSON to XML'
        },
        {
          name: 'JSON To BASE64',
          icon: CodeOutlined,
          description: 'Convert JSON to BASE64'
        },
        {
          name: 'JSON To Excel',
          icon: FileExcelOutlined,
          description: 'Convert JSON to Excel'
        }
      ]
    },
    {
      name: 'pdf_converter',
      icon: FilePdfOutlined,
      description: 'pdf_converter_desc',
      tools: [
        {
          name: 'PDF To DOC',
          icon: FilePdfOutlined,
          description: 'Convert PDF to DOC'
        },
        {
          name: 'PDF To PNG',
          icon: FilePdfOutlined,
          description: 'Convert PDF to PNG'
        },
        {
          name: 'PDF To DOCX',
          icon: FilePdfOutlined,
          description: 'Convert PDF to DOCX'
        },
        {
          name: 'PDF To JPG',
          icon: FilePdfOutlined,
          description: 'Convert PDF to JPG'
        },
        {
          name: 'PDF To SVG',
          icon: FilePdfOutlined,
          description: 'Convert PDF to SVG'
        },
        {
          name: 'PDF To JSON',
          icon: FilePdfOutlined,
          description: 'Convert PDF to JSON'
        },
        {
          name: 'PDF To EPUB',
          icon: FilePdfOutlined,
          description: 'Convert PDF to EPUB'
        },
        {
          name: 'PDF To TXT',
          icon: FilePdfOutlined,
          description: 'Convert PDF to TXT'
        },
        {
          name: 'PDF To BASE64',
          icon: FilePdfOutlined,
          description: 'Convert PDF to BASE64'
        },
        {
          name: 'PDF To TIFF',
          icon: FilePdfOutlined,
          description: 'Convert PDF to TIFF'
        },
        {
          name: 'PDF To BMP',
          icon: FilePdfOutlined,
          description: 'Convert PDF to BMP'
        },
        {
          name: 'PDF To MD',
          icon: FilePdfOutlined,
          description: 'Convert PDF to MD'
        },
        {
          name: 'PDF To HTML',
          icon: FilePdfOutlined,
          description: 'Convert PDF to HTML'
        },
        {
          name: 'PDF To PPT',
          icon: FilePdfOutlined,
          description: 'Convert PDF to PPT'
        },
        {
          name: 'PDF To GIF',
          icon: FilePdfOutlined,
          description: 'Convert PDF to GIF'
        },
        {
          name: 'PDF To RTF',
          icon: FilePdfOutlined,
          description: 'Convert PDF to RTF'
        },
        {
          name: 'PDF To WEBP',
          icon: FilePdfOutlined,
          description: 'Convert PDF to WEBP'
        },
        {
          name: 'PDF To Excel',
          icon: FileExcelOutlined,
          description: 'Convert PDF to Excel'
        }
      ]
    },
    {
      name: 'ppt_converter',
      icon: FilePdfOutlined,
      description: 'ppt_converter_desc',
      tools: [
        {
          name: 'PPT To PDF',
          icon: FilePdfOutlined,
          description: 'Convert PPT to PDF'
        },
        {
          name: 'PPT To PNG',
          icon: FileImageOutlined,
          description: 'Convert PPT to PNG'
        },
        {
          name: 'PPT To JPG',
          icon: FileImageOutlined,
          description: 'Convert PPT to JPG'
        },
        {
          name: 'PPT To Video',
          icon: FileImageOutlined,
          description: 'Convert PPT to Video (MP4)'
        }
      ]
    },
    {
      name: 'excel_converter',
      icon: FileExcelOutlined,
      description: 'excel_converter_desc',
      tools: [
        {
          name: 'Excel To PDF',
          icon: FilePdfOutlined,
          description: 'Convert Excel to PDF'
        },
        {
          name: 'Excel To PNG',
          icon: FileImageOutlined,
          description: 'Convert Excel to PNG'
        },
        {
          name: 'Excel To JPG',
          icon: FileImageOutlined,
          description: 'Convert Excel to JPG'
        },
        {
          name: 'Excel To PPT',
          icon: FileExcelOutlined,
          description: 'Convert Excel to PPT'
        }
      ]
    },
    {
      name: 'txt_converter',
      icon: FileTextOutlined,
      description: 'txt_converter_desc',
      tools: [
        {
          name: 'TXT To PDF',
          icon: FilePdfOutlined,
          description: 'Convert TXT to PDF'
        },
        {
          name: 'TXT To SPEECH',
          icon: FileTextOutlined,
          description: 'Convert TXT to SPEECH'
        },
        {
          name: 'TXT To JPG',
          icon: FileImageOutlined,
          description: 'Convert TXT to JPG'
        },
        {
          name: 'TXT To PNG',
          icon: FileImageOutlined,
          description: 'Convert TXT to PNG'
        },
        {
          name: 'TXT To ASCII',
          icon: FileTextOutlined,
          description: 'Convert TXT to ASCII'
        },
        {
          name: 'TXT To BINARY',
          icon: FileTextOutlined,
          description: 'Convert TXT to BINARY'
        },
        {
          name: 'TXT To CSV',
          icon: FileExcelOutlined,
          description: 'Convert TXT to CSV'
        },
        {
          name: 'TXT To HEX',
          icon: FileTextOutlined,
          description: 'Convert TXT to HEX'
        },
        {
          name: 'TXT To HTML',
          icon: CodeOutlined,
          description: 'Convert TXT to HTML'
        },
      ]
    },
    {
      name: 'xml_converter',
      icon: CodeOutlined,
      description: 'xml_converter_desc',
      tools: [
        {
          name: 'XML To JSON',
          icon: CodeOutlined,
          description: 'Convert XML to JSON'
        },
        {
          name: 'XML To YAML',
          icon: CodeOutlined,
          description: 'Convert XML to YAML'
        },
        {
          name: 'XML To CSV',
          icon: FileExcelOutlined,
          description: 'Convert XML to CSV'
        },
        {
          name: 'XML To HTML',
          icon: CodeOutlined,
          description: 'Convert XML to HTML'
        },
        {
          name: 'XML To TEXT',
          icon: CodeOutlined,
          description: 'Convert XML to TEXT'
        },
        {
          name: 'XML To PDF',
          icon: FilePdfOutlined,
          description: 'Convert XML to PDF'
        },
        {
          name: 'XML To XLSX',
          icon: FileExcelOutlined,
          description: 'Convert XML to XLSX'
        },
        {
          name: 'XML To PNG',
          icon: FileImageOutlined,
          description: 'Convert XML to PNG'
        },
        {
          name: 'XML To JPG',
          icon: FileImageOutlined,
          description: 'Convert XML to JPG'
        },
        {
          name: 'XML To SVG',
          icon: FileImageOutlined,
          description: 'Convert XML to SVG'
        },
      ]
    },
  ]
};

export default categories;
