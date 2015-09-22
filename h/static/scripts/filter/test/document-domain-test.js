'use strict';

describe('documentDomain', function() {

  before(function() {
    angular.module('h', []).filter(
        'documentDomain', require('../document-domain'));
  });

  beforeEach(angular.mock.module('h'));

  function getFilter() {
    var filter;
    angular.mock.inject(function($filter) {
      filter = $filter('documentDomain');
    });
    return filter;
  }

  it('returns the domain in braces', function() {
    var domain = getFilter()({
      domain: 'example.com'
    });

    assert(domain === '(example.com)');
  });

  it('returns an empty string if domain and title are the same', function() {
    var domain = getFilter()({
      domain: 'example.com',
      title: 'example.com'
    });

    assert(domain === '');
  });

  it('returns an empty string if the document has no domain', function() {
    var domain = getFilter()({
      title: 'example.com'
    });

    assert(domain === '');
  });
});
