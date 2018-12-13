import _config as conf
from model.source_rva import RVA
from model.source_rdf_file import RDFFile


def get_vocabulary(vocab_id):
    source_type = conf.VOCABS[vocab_id].get('source')

    if source_type == conf.VocabSource.FILE:
        v = RDFFile().get_vocabulary(vocab_id)
    elif source_type == conf.VocabSource.RVA:
        v = RVA().get_vocabulary(vocab_id)
    # TODO: add other sources
    else:
        v = None

    return v


def get_object_class(vocab_id, uri):
    source_type = conf.VOCABS[vocab_id].get('source')

    if source_type == conf.VocabSource.FILE:
        c = RVA().get_object_class(vocab_id, uri)
    elif source_type == conf.VocabSource.RVA:
        c = RDFFile().get_object_class(vocab_id, uri)
    else:
        # no other sources for now
        c = None

    return c


def get_concept(vocab_id, uri):
    source_type = conf.VOCABS[vocab_id].get('source')

    if source_type == conf.VocabSource.FILE:
        c = RVA().get_concept(vocab_id, uri)
    elif source_type == conf.VocabSource.RVA:
        c = RDFFile().get_concept(vocab_id, uri)
    else:
        # no other sources for now
        c = None

    return c
