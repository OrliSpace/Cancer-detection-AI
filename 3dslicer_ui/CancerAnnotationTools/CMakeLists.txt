cmake_minimum_required(VERSION 3.20.6...3.22.6 FATAL_ERROR)

project(DICOMLabeling)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/CancerAnnotationTools")
set(EXTENSION_CONTRIBUTORS "Orli Davidpur, Roei Kadosh")
set(EXTENSION_DESCRIPTION "This extension is designed to provide an easy and efficient environment for annotating DICOM data in 3D Slicer, while also collecting patient information. It was developed as part of the project by Orli Davidpur and Roei Kadosh at Bar-Ilan University.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/CancerAnnotationTools.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/CancerAnnotationTools/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(PatientTagger)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
