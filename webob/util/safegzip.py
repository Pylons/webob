"""
GZip that doesn't include the timestamp
"""
import gzip

class GzipFile(gzip.GzipFile):
    def _write_gzip_header(self):
        self.fileobj.write('\x1f\x8b') # magic header
        self.fileobj.write('\x08') # compression method
        if hasattr(self, 'name'):
            # 2.6
            fname = self.name
            if fname.endswith(".gz"):
                fname = fname[:-3]
        else:
            fname = self.filename[:-3]
        flags = 0
        if fname:
            flags = gzip.FNAME
        self.fileobj.write(chr(flags))
        ## This is what WebOb patches:
        gzip.write32u(self.fileobj, long(0))
        self.fileobj.write('\x02\xff')
        if fname:
            self.fileobj.write(fname + '\x00')
