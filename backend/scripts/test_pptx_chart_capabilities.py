import io
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.chart.data import CategoryChartData
from pptx.oxml import parse_xml

prs = Presentation()
slide = prs.slides.add_slide(prs.slide_layouts[6])

# 1. Test Connector with arrowhead
c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(1), Inches(1), Inches(3), Inches(1))
ln = c._element.spPr.ln
if ln is not None:
    head = parse_xml('<a:headEnd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" type="triangle" w="med" len="med"/>')
    ln.append(head)
print("Connector and arrowhead OK")

# 2. Test Native Chart (Clustered Column)
chart_data = CategoryChartData()
chart_data.categories = ['Q1', 'Q2', 'Q3', 'Q4']
chart_data.add_series('Revenue', (10.5, 14.2, 18.0, 22.4))
chart_data.add_series('Expenses', (8.1, 9.5, 11.2, 13.0))

x, y, cx, cy = Inches(4), Inches(1), Inches(5), Inches(4)
chart_shape = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, cx, cy, chart_data
)
chart = chart_shape.chart
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.TOP
chart.legend.include_in_layout = False
print("Native Clustered Column Chart OK, shape_id:", chart_shape.shape_id)

# 3. Test Save and Reload
buf = io.BytesIO()
prs.save(buf)
reopened = Presentation(io.BytesIO(buf.getvalue()))
print("Round-trip saved and reopened OK, slide shapes:", len(reopened.slides[0].shapes))
