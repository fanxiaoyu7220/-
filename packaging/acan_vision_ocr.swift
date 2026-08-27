import AppKit
import Foundation
import Vision


guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write(Data("usage: acan-vision-ocr <image>\n".utf8))
    exit(64)
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
guard let image = NSImage(contentsOf: imageURL) else {
    FileHandle.standardError.write(Data("unable to read image\n".utf8))
    exit(66)
}

var imageRect = NSRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &imageRect, context: nil, hints: nil) else {
    FileHandle.standardError.write(Data("unable to decode image\n".utf8))
    exit(65)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true

do {
    try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
    for observation in request.results ?? [] {
        if let candidate = observation.topCandidates(1).first {
            print(candidate.string)
        }
    }
} catch {
    FileHandle.standardError.write(Data("Vision OCR failed: \(error)\n".utf8))
    exit(1)
}
