#!/usr/bin/env bash
# pdf-to-pptx.sh - With blank slide template and better image handling
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ $# -lt 1 ]; then
    echo "Usage: $0 input.pdf [output.pptx]"
    exit 1
fi

INPUT_PDF="$1"
OUTPUT_PPTX="${2:-${INPUT_PDF%.pdf}.pptx}"

if [ ! -f "$INPUT_PDF" ]; then
    echo -e "${RED}Error: $INPUT_PDF not found${NC}"
    exit 1
fi

TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

TEMP_SVG="$TEMP_DIR/temp.svg"
OUTPUT_SVG="$TEMP_DIR/figure.svg"

echo -e "${GREEN}Converting $INPUT_PDF → $OUTPUT_PPTX${NC}"

# Step 1: PDF → SVG
echo "[1/3] PDF → SVG"
inkscape "$INPUT_PDF" \
    --export-type=svg \
    --export-filename="$TEMP_SVG" \
    --export-plain-svg

# Step 2: Convert text to paths (but keep images as images)
echo "[2/3] Converting text to paths"
inkscape "$TEMP_SVG" \
    --actions="select-all;object-to-path;export-filename:$OUTPUT_SVG;export-plain-svg;export-do" \
    --batch-process

if [ ! -f "$OUTPUT_SVG" ]; then
    echo -e "${RED}Error: SVG conversion failed${NC}"
    exit 1
fi

# Step 3: Import to LibreOffice, break ONCE, save as PPTX
echo "[3/3] Importing to LibreOffice and breaking apart"

cat > "$TEMP_DIR/process.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
import uno
from com.sun.star.beans import PropertyValue
import sys
import time
import subprocess
import os
import xml.etree.ElementTree as ET

def get_svg_dimensions(svg_path):
    """Extract width and height from SVG file"""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        width = root.get('width', '100')
        height = root.get('height', '100')
        
        width = float(''.join(c for c in width if c.isdigit() or c == '.'))
        height = float(''.join(c for c in height if c.isdigit() or c == '.'))
        
        return width, height
    except:
        return 210, 297

def svg_to_pptx(svg_path, output_pptx):
    svg_width, svg_height = get_svg_dimensions(svg_path)
    aspect_ratio = svg_width / svg_height
    
    print(f"SVG dimensions: {svg_width} x {svg_height}, aspect ratio: {aspect_ratio:.2f}")
    
    # Start LibreOffice
    lo_proc = subprocess.Popen([
        'soffice',
        '--headless',
        '--invisible',
        '--norestore',
        '--accept=socket,host=localhost,port=2002;urp;'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(3)
    
    try:
        # Connect
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local)
        
        ctx = resolver.resolve(
            "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        
        # Create new Impress presentation
        doc = desktop.loadComponentFromURL("private:factory/simpress", "_blank", 0, tuple())
        
        time.sleep(1)
        
        # Get first slide
        draw_pages = doc.getDrawPages()
        page = draw_pages.getByIndex(0)
        
        # Set slide to blank layout (remove default text boxes)
        # Layout 20 is typically "Blank" in LibreOffice Impress
        try:
            layouts = doc.getMasterPages().getByIndex(0).getLayouts()
            blank_layout = None
            
            # Try to find blank layout
            for i in range(layouts.getCount()):
                layout = layouts.getByIndex(i)
                layout_name = layout.getName()
                if 'blank' in layout_name.lower() or 'leer' in layout_name.lower():
                    blank_layout = layout
                    break
            
            if blank_layout:
                page.setLayout(20)  # Blank layout code
        except Exception as e:
            print(f"Note: Could not set blank layout: {e}")
            # Remove any default shapes manually
            while page.getCount() > 0:
                page.remove(page.getByIndex(0))
        
        # Get slide dimensions
        slide_width = page.Width
        slide_height = page.Height
        
        print(f"Slide dimensions: {slide_width} x {slide_height}")
        
        # Calculate size to fit slide while preserving aspect ratio
        max_width = slide_width * 0.9
        max_height = slide_height * 0.9
        
        if aspect_ratio > (max_width / max_height):
            img_width = int(max_width)
            img_height = int(max_width / aspect_ratio)
        else:
            img_height = int(max_height)
            img_width = int(max_height * aspect_ratio)
        
        # Center on slide
        x_pos = int((slide_width - img_width) / 2)
        y_pos = int((slide_height - img_height) / 2)
        
        print(f"Image will be: {img_width} x {img_height} at position ({x_pos}, {y_pos})")
        
        # Insert SVG
        svg_url = uno.systemPathToFileUrl(os.path.abspath(svg_path))
        
        graphic_shape = doc.createInstance("com.sun.star.drawing.GraphicObjectShape")
        graphic_shape.GraphicURL = svg_url
        
        # Set position and size
        graphic_shape.setPosition(uno.createUnoStruct('com.sun.star.awt.Point', x_pos, y_pos))
        graphic_shape.setSize(uno.createUnoStruct('com.sun.star.awt.Size', img_width, img_height))
        
        page.add(graphic_shape)
        
        time.sleep(0.5)
        
        # Select the shape
        controller = doc.getCurrentController()
        controller.select(graphic_shape)
        
        frame = controller.getFrame()
        dispatcher = smgr.createInstanceWithContext(
            "com.sun.star.frame.DispatchHelper", ctx)
        
        # Break apart ONCE
        print("Breaking apart object...")
        dispatcher.executeDispatch(frame, ".uno:Break", "", 0, tuple())
        
        time.sleep(0.5)
        
        # Save as PPTX
        output_url = uno.systemPathToFileUrl(os.path.abspath(output_pptx))
        
        save_props = (
            PropertyValue("FilterName", 0, "Impress MS PowerPoint 2007 XML", 0),
            PropertyValue("Overwrite", 0, True, 0),
        )
        
        doc.storeToURL(output_url, save_props)
        doc.close(True)
        
        print(f"✓ Created: {output_pptx}")
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
    finally:
        lo_proc.terminate()
        lo_proc.wait()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(1)
    
    success = svg_to_pptx(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
PYTHON_EOF

# Kill existing LibreOffice
killall soffice soffice.bin 2>/dev/null || true
sleep 1

# Process
python3 "$TEMP_DIR/process.py" "$OUTPUT_SVG" "$(realpath "$OUTPUT_PPTX")"

if [ -f "$OUTPUT_PPTX" ]; then
    FILE_SIZE=$(du -h "$OUTPUT_PPTX" | cut -f1)
    echo ""
    echo -e "${GREEN}✓ Done: $OUTPUT_PPTX ($FILE_SIZE)${NC}"
    echo -e "${YELLOW}Slide uses blank template${NC}"
    echo ""
    echo -e "${YELLOW}Note about PNG images:${NC}"
    echo -e "${YELLOW}The 'object-to-path' command converts text but may affect embedded images.${NC}"
    echo -e "${YELLOW}If PNG images disappear:${NC}"
    echo -e "${YELLOW}  1. Make sure PNGs are embedded (not linked) in your Inkscape file${NC}"
    echo -e "${YELLOW}  2. Try: Edit → Select Same → Object Type → Images, then exclude from path conversion${NC}"
    echo -e "${YELLOW}  3. Or skip text-to-path and accept pixelated text for figures with many PNGs${NC}"
    
else
    echo -e "${RED}Error: PPTX creation failed${NC}"
    exit 1
fi
