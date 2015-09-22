'use strict';

describe('documentTitle', function() {

  before(function() {
    angular.module('h', []).filter(
        'documentTitle', require('../document-title'));
  });

  beforeEach(angular.mock.module('h'));

  function getFilter() {
    var filter;
    angular.mock.inject(function($filter) {
      filter = $filter('documentTitle');
    });
    return filter;
  }

  it('returns the title linked if the document has title and uri', function() {
    var title = getFilter()({
      title: 'title',
      uri: 'http://example.com/example.html'
    });

    assert(title === 'on &ldquo;<a target="_blank" ' +
                     'href="http://example.com/example.html">' +
                     'title</a>&rdquo;');
  });

  it('returns the title linked if the document has an https uri', function() {
    var title = getFilter()({
      title: 'title',
      uri: 'https://example.com/example.html'
    });

    assert(title === 'on &ldquo;<a target="_blank" '+
                     'href="https://example.com/example.html">' +
                     'title</a>&rdquo;');
  });

  it('returns the title unlinked if doc has title but no uri', function() {
    var title = getFilter()({
      title: 'title',
    });

    assert(title === 'on &ldquo;title&rdquo;');
  });

  it('returns the title unlinked if doc has non-http uri', function() {
    var title = getFilter()({
      title: 'title',
      uri: 'file:///home/bob/Documents/example.pdf'
    });

    assert(title === 'on &ldquo;title&rdquo;');
  });

  it('returns the title linked if the document has title and uri', function() {
    var title = getFilter()({
      title: 'title',
      uri: 'http://example.com/example.html'
    });

    assert(title === 'on &ldquo;<a target="_blank" ' +
                     'href="http://example.com/example.html">' +
                     'title</a>&rdquo;');
  });

  it('returns an empty string if the document has no title', function() {
    var title = getFilter()({
      uri: 'http://example.com/example.html'
    });

    assert(title === '');
  });
});
