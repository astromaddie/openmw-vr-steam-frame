#include <osg/Image>
#include <osgDB/ReadFile>
#include <osgDB/WriteFile>
#include <osgDB/Registry>
#include <cstring>
#include <iostream>

USE_OSGPLUGIN(png)

int main(int argc, char** argv)
{
    if (argc < 2) return 1;
    osg::ref_ptr<osg::Image> image = new osg::Image;
    image->allocateImage(2, 2, 1, GL_RGBA, GL_UNSIGNED_BYTE);
    // GL readback order: bottom row red, top row blue.
    const unsigned char red[] = {255, 0, 0, 255};
    const unsigned char blue[] = {0, 0, 255, 255};
    for (int x = 0; x < 2; ++x)
    {
        std::memcpy(image->data(x, 0), red, 4);
        std::memcpy(image->data(x, 1), blue, 4);
    }
    if (argc > 2) image->flipVertical(); // negative control, reproducing the bug
    if (!osgDB::writeImageFile(*image, argv[1])) return 1;
    osg::ref_ptr<osg::Image> decoded = osgDB::readImageFile(argv[1]);
    if (!decoded || std::memcmp(decoded->data(0, 0), red, 4)
        || std::memcmp(decoded->data(0, 1), blue, 4)) return 2;
    std::cout << "PASS: GL row order survives OSG PNG write/read\n";
}
