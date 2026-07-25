#!/usr/bin/env swift

import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count > 1 else {
    fputs("usage: classify_scene.swift IMAGE...\n", stderr)
    exit(2)
}

for argument in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: argument)
    guard
        let image = NSImage(contentsOf: url),
        let data = image.tiffRepresentation,
        let bitmap = NSBitmapImageRep(data: data),
        let cgImage = bitmap.cgImage
    else {
        print("\(argument)\terror=unreadable")
        continue
    }

    let classify = VNClassifyImageRequest()
    let faces = VNDetectFaceRectanglesRequest()
    let handler = VNImageRequestHandler(cgImage: cgImage)

    do {
        try handler.perform([classify, faces])
        let classes = (classify.results ?? []).prefix(12).map {
            "\($0.identifier.replacingOccurrences(of: ",", with: "/")):\(String(format: "%.3f", $0.confidence))"
        }.joined(separator: ",")
        let faceResults = faces.results ?? []
        let largestFace = faceResults.map {
            $0.boundingBox.width * $0.boundingBox.height
        }.max() ?? 0
        print(
            "\(argument)\tfaces=\(faceResults.count)\tlargest_face=\(String(format: "%.4f", largestFace))\tlabels=\(classes)"
        )
    } catch {
        print("\(argument)\terror=\(error.localizedDescription)")
    }
}
