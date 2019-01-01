# Look Up at Space
Infinity scroll website that lets you view the universe in all its glory. [View the website here.](http://lookupat.space/)

<img src="https://i.imgur.com/zVAYVxQ.jpg">

The scraping script relies on regular expressions and requests to the heavy
lifting. After obtaining the HTML from the 
[Archive Page](http://apod.nasa.gov/apod/archivepix.html), the script will 
make GET requests to each subsequent page within the archive
list for that page's HTML. After retrieval, more regular expressions are used 
to obtain the image URL for the large space-related picture that NASA had posted
for that day.

The collected image URLs, titles, and dates are then saved and serialized into
JSON for later retrieval and for use in posting to social media websites.

For the love of space, this is fun!


## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D

## License

Available for personal-use only. Do not reproduce, re-use, re-purpose, or sell
SpaceScrape. Contributions may only be made to this repository.

## Space is Beautiful

<p align="center">
    <img src="http://apod.nasa.gov/apod/image/1608/M63LRGBVermetteR.jpg" alt="A screenshot showing PySee">
</p>
