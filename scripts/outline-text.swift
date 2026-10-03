// Shape text with Core Text and export glyph outlines, fixing typography in SVG.
import Foundation
import CoreText
import CoreGraphics

struct Request: Decodable {
    let x: Double
    let y: Double
    let content: String
    let size: Double
    let weight: Int
    let mono: Bool
    let tracking: Double
}

struct Result: Encodable {
    let path: String
    let width: Double
    let fonts: [String]
    let bounds: [Double]
}

func number(_ value: CGFloat) -> String {
    let rounded = abs(value) < 0.005 ? 0 : value
    return String(format: "%.2f", Double(rounded))
        .replacingOccurrences(of: #"\.?0+$"#, with: "", options: .regularExpression)
        .replacingOccurrences(of: #"^(-?)0\."#, with: "$1.", options: .regularExpression)
}

func commands(_ path: CGPath) -> String {
    var parts: [String] = []
    var current = CGPoint.zero
    var start = CGPoint.zero
    var first = true
    func point(_ p: CGPoint) -> String { "\(number(p.x)) \(number(p.y))" }
    func rounded(_ p: CGPoint) -> CGPoint {
        CGPoint(x: (p.x * 100).rounded() / 100, y: (p.y * 100).rounded() / 100)
    }
    func relative(_ p: CGPoint) -> String {
        let p = rounded(p)
        return point(CGPoint(x: p.x - current.x, y: p.y - current.y))
    }
    path.applyWithBlock { pointer in
        let element = pointer.pointee
        switch element.type {
        case .moveToPoint:
            parts.append((first ? "M" + point(rounded(element.points[0])) : "m" + relative(element.points[0])))
            current = rounded(element.points[0]); start = current; first = false
        case .addLineToPoint:
            parts.append("l" + relative(element.points[0]))
            current = rounded(element.points[0])
        case .addQuadCurveToPoint:
            parts.append("q" + relative(element.points[0]) + " " + relative(element.points[1]))
            current = rounded(element.points[1])
        case .addCurveToPoint:
            parts.append("c" + relative(element.points[0]) + " " + relative(element.points[1]) + " " + relative(element.points[2]))
            current = rounded(element.points[2])
        case .closeSubpath: parts.append("z"); current = start
        @unknown default: break
        }
    }
    return parts.joined().replacingOccurrences(of: " -", with: "-")
}

for path in ["/Library/Fonts/SF-Pro-Text-Regular.otf", "/Library/Fonts/SF-Pro-Text-Semibold.otf"] {
    CTFontManagerRegisterFontsForURL(URL(fileURLWithPath: path) as CFURL, .process, nil)
}

let requests = try JSONDecoder().decode([Request].self, from: FileHandle.standardInput.readDataToEndOfFile())
let results = requests.map { request -> Result in
    let name = request.mono ? "Menlo-Regular" : request.weight >= 600 ? "SFProText-Semibold" : "SFProText-Regular"
    let font = CTFontCreateWithName(name as CFString, request.size, nil)
    var attributes: [NSAttributedString.Key: Any] = [
        NSAttributedString.Key(kCTFontAttributeName as String): font,
        NSAttributedString.Key(kCTLanguageAttributeName as String): "zh-Hans",
    ]
    if request.tracking != 0 {
        attributes[NSAttributedString.Key(kCTKernAttributeName as String)] = request.tracking
    }
    let line = CTLineCreateWithAttributedString(NSAttributedString(string: request.content, attributes: attributes))
    let runs = CTLineGetGlyphRuns(line) as! [CTRun]
    var paths: [String] = []
    var fonts = Set<String>()
    var bounds = CGRect.null
    for run in runs {
        let runAttributes = CTRunGetAttributes(run) as NSDictionary
        let runFont = runAttributes[kCTFontAttributeName] as! CTFont
        fonts.insert(CTFontCopyPostScriptName(runFont) as String)
        let count = CTRunGetGlyphCount(run)
        var glyphs = [CGGlyph](repeating: 0, count: count)
        var positions = [CGPoint](repeating: .zero, count: count)
        CTRunGetGlyphs(run, CFRange(location: 0, length: 0), &glyphs)
        CTRunGetPositions(run, CFRange(location: 0, length: 0), &positions)
        for index in 0..<count {
            guard let glyph = CTFontCreatePathForGlyph(runFont, glyphs[index], nil) else { continue }
            var transform = CGAffineTransform(a: 1, b: 0, c: 0, d: -1,
                tx: request.x + positions[index].x, ty: request.y - positions[index].y)
            guard let positioned = glyph.copy(using: &transform) else { continue }
            paths.append(commands(positioned))
            bounds = bounds.union(positioned.boundingBoxOfPath)
        }
    }
    return Result(path: paths.joined(), width: CTLineGetTypographicBounds(line, nil, nil, nil),
        fonts: fonts.sorted(), bounds: bounds.isNull ? [] : [bounds.minX, bounds.minY, bounds.maxX, bounds.maxY])
}
FileHandle.standardOutput.write(try JSONEncoder().encode(results))
