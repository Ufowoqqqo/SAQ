#include <faiss/IndexIVFPQ.h>
#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>

#include <exception>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <typeinfo>

int main(int argc, char** argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument(
                    "usage: structured_2d_inspect_opq "
                    "<index> <opq>");
        std::unique_ptr<faiss::Index> index_owner(
                faiss::read_index(argv[1]));
        std::unique_ptr<faiss::VectorTransform> opq_owner(
                faiss::read_VectorTransform(argv[2]));
        auto* index =
                dynamic_cast<faiss::IndexIVFPQ*>(
                        index_owner.get());
        auto* opq =
                dynamic_cast<faiss::LinearTransform*>(
                        opq_owner.get());
        std::cout << "index_type\t" << typeid(*index_owner).name()
                  << "\nopq_type\t" << typeid(*opq_owner).name()
                  << '\n';
        if (index == nullptr || opq == nullptr)
            return 2;
        std::cout
                << "d\tnlist\tntotal\tby_residual\tM\tnbits"
                   "\tpq_centroid_values\topq_values"
                   "\topq_trained\topq_orthonormal\n"
                << index->d << '\t' << index->nlist << '\t'
                << index->ntotal << '\t' << index->by_residual
                << '\t' << index->pq.M << '\t'
                << index->pq.nbits << '\t'
                << index->pq.centroids.size() << '\t'
                << opq->A.size() << '\t' << opq->is_trained
                << '\t' << opq->is_orthonormal << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_inspect_opq: "
                  << error.what() << '\n';
        return 1;
    }
}
