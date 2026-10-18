function Image(image)
  if FORMAT:match("latex") and image.src:lower():match("%.svg$") then
    image.src = image.src:sub(1, -5) .. ".pdf"
  end
  return image
end
